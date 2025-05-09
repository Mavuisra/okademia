from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
import os
import json
import tempfile
import shutil

from belletin.models import (
    AcademicYear, Faculty, Department, Promotion, Student, UE, Grade, Professor,
    Course, OfflineQueue, JuryMember, Deliberation, StudentDeliberation
)
from belletin.offline import OfflineMixin, OfflineSynchronizer
from belletin.management.commands.backup_database import Command as BackupCommand
from belletin.management.commands.sync_offline_data import Command as SyncCommand


class ModelTestCase(TestCase):
    """Test suite for core model functionality"""
    
    def setUp(self):
        # Create base data
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025", 
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(name="Sciences et Techniques")
        self.department = Department.objects.create(name="Informatique", faculty=self.faculty)
        
        self.promotion = Promotion.objects.create(
            level="L1",
            department=self.department,
            academic_year=self.academic_year
        )
        
        # Create users
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        
        self.professor_user = User.objects.create_user(
            username="prof", email="prof@test.com", password="prof123"
        )
        
        self.student_user = User.objects.create_user(
            username="student", email="student@test.com", password="student123"
        )
        
        # Create profiles
        self.professor = Professor.objects.create(
            user=self.professor_user,
            department=self.department
        )
        
        self.student = Student.objects.create(
            user=self.student_user,
            matricule="STD001",
            promotion=self.promotion,
            current_academic_year=self.academic_year,
            admission_year=self.academic_year
        )
        
        # Create courses and UEs
        self.ue = UE.objects.create(
            code="INF101",
            title="Introduction à l'informatique",
            credits=6,
            semester=1,
            promotion=self.promotion
        )
        
        self.course = Course.objects.create(
            ue=self.ue,
            professor=self.professor,
            academic_year=self.academic_year
        )

    def test_academic_year_current_flag(self):
        """Test that only one academic year can be current"""
        new_year = AcademicYear.objects.create(
            name="2025-2026", 
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_current=True
        )
        
        # Refresh from database
        self.academic_year.refresh_from_db()
        
        # Check that original academic year is no longer current
        self.assertFalse(self.academic_year.is_current)
        self.assertTrue(new_year.is_current)

    def test_grade_auto_calculation(self):
        """Test grade average auto-calculation"""
        grade = Grade.objects.create(
            student=self.student,
            ue=self.ue,
            cc=14.0,
            mc=16.0
        )
        
        self.assertEqual(grade.moyenne, 15.0)
        self.assertEqual(grade.resultat, 'VALIDÉ')
        
        # Test failing grade
        grade.cc = 8.0
        grade.mc = 8.0
        grade.save()
        
        self.assertEqual(grade.moyenne, 8.0)
        self.assertEqual(grade.resultat, 'NON VALIDÉ')


class OfflineQueueTestCase(TestCase):
    """Test the offline queue functionality"""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        
        # Create a client and log in
        self.client = Client()
        self.client.login(username="testuser", password="password123")
        
        # Create sample data in the queue
        self.queue_item = OfflineQueue.objects.create(
            operation_type="CREATE",
            model_name="Grade",
            object_id="",
            user=self.user,
            data={
                "student_id": 1,
                "ue_id": 1,
                "cc": 12.5,
                "mc": 14.0
            },
            status="PENDING"
        )
    
    def test_offline_mixin(self):
        """Test the OfflineMixin functionality"""
        mixin = OfflineMixin()
        
        # Create a mock request with offline mode enabled
        mock_request = MagicMock()
        mock_request.POST = {"offline_mode": "true"}
        mock_request.headers = {}
        mock_request.user = self.user
        
        # Test offline detection
        self.assertTrue(mixin.is_offline_request(mock_request))
        
        # Test header-based detection
        mock_request.POST = {}
        mock_request.headers = {"X-Offline-Mode": "true"}
        self.assertTrue(mixin.is_offline_request(mock_request))
        
        # Test queuing functionality
        queue_item = mixin.queue_offline_operation(
            mock_request,
            "UPDATE",
            "Grade",
            1,
            {"cc": 15.0}
        )
        
        self.assertEqual(queue_item.operation_type, "UPDATE")
        self.assertEqual(queue_item.model_name, "Grade")
        self.assertEqual(queue_item.object_id, "1")
        self.assertEqual(queue_item.user, self.user)
        self.assertEqual(queue_item.data, {"cc": 15.0})
        self.assertEqual(queue_item.status, "PENDING")
    
    @patch("belletin.offline.OfflineSynchronizer._process_create")
    def test_synchronizer_process(self, mock_process_create):
        """Test the OfflineSynchronizer process_queue method"""
        # Call the process_queue method
        success, failure, remaining = OfflineSynchronizer.process_queue()
        
        # Check that the _process_create method was called
        self.assertEqual(mock_process_create.call_count, 1)
        
        # Check the queue item was processed
        self.queue_item.refresh_from_db()
        self.assertEqual(self.queue_item.status, "COMPLETED")
        
        # Check the stats are correct
        self.assertEqual(success, 1)
        self.assertEqual(failure, 0)
        self.assertEqual(remaining, 0)
    
    @patch("belletin.offline.OfflineSynchronizer._process_create")
    def test_synchronizer_error_handling(self, mock_process_create):
        """Test error handling in the synchronizer"""
        # Make the process method raise an exception
        mock_process_create.side_effect = Exception("Test error")
        
        # Call the process_queue method
        success, failure, remaining = OfflineSynchronizer.process_queue()
        
        # Check the queue item was marked as failed
        self.queue_item.refresh_from_db()
        self.assertEqual(self.queue_item.status, "FAILED")
        self.assertEqual(self.queue_item.error_message, "Test error")
        self.assertEqual(self.queue_item.retry_count, 1)
        
        # Check the stats are correct
        self.assertEqual(success, 0)
        self.assertEqual(failure, 1)
        self.assertEqual(remaining, 0)


class SyncCommandTestCase(TestCase):
    """Test the synchronization management command"""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        
        # Create sample data in the queue
        for i in range(5):
            OfflineQueue.objects.create(
                operation_type="CREATE",
                model_name="Grade",
                object_id="",
                user=self.user,
                data={f"field{i}": f"value{i}"},
                status="PENDING"
            )
    
    @patch("belletin.offline.OfflineSynchronizer.process_queue")
    def test_command_execution(self, mock_process_queue):
        """Test execution of the sync_offline_data command"""
        # Configure the mock to return some stats
        mock_process_queue.return_value = (3, 1, 1)
        
        # Create the command
        command = SyncCommand()
        
        # Call the command
        success, failure, remaining = command.handle(limit=10)
        
        # Check the process_queue method was called with the right limit
        mock_process_queue.assert_called_once_with(limit=10)
        
        # Check the command returned the right stats
        self.assertEqual(success, 3)
        self.assertEqual(failure, 1)
        self.assertEqual(remaining, 1)


class BackupCommandTestCase(TestCase):
    """Test the database backup command"""
    
    def setUp(self):
        # Create a temporary directory for backups
        self.temp_dir = tempfile.mkdtemp()
        
        # Override the settings
        self.settings_patcher = patch("django.conf.settings.BASE_DIR", self.temp_dir)
        self.settings_patcher.start()
    
    def tearDown(self):
        # Stop the patch
        self.settings_patcher.stop()
        
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    @patch("belletin.management.commands.backup_database.shutil.copy2")
    @patch("django.db.connection")
    def test_sqlite_backup(self, mock_connection, mock_copy):
        """Test SQLite database backup"""
        # Configure the mock connection to appear as SQLite
        mock_connection.settings_dict = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "db.sqlite3"
        }
        
        # Create the command
        command = BackupCommand()
        
        # Call the command
        command.handle(keep=3)
        
        # Check that copy2 was called
        mock_copy.assert_called_once()
        
        # Check backup directory was created
        backup_dir = os.path.join(self.temp_dir, "backups")
        self.assertTrue(os.path.exists(backup_dir))
    
    @patch("belletin.management.commands.backup_database.subprocess.run")
    @patch("django.db.connection")
    def test_postgres_backup(self, mock_connection, mock_run):
        """Test PostgreSQL database backup"""
        # Configure the mock connection to appear as PostgreSQL
        mock_connection.settings_dict = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "test_db",
            "USER": "test_user",
            "PASSWORD": "test_password",
            "HOST": "localhost"
        }
        
        # Create the command
        command = BackupCommand()
        
        # Call the command
        command.handle(keep=3)
        
        # Check that subprocess.run was called
        mock_run.assert_called_once()
        
        # Check backup directory was created
        backup_dir = os.path.join(self.temp_dir, "backups")
        self.assertTrue(os.path.exists(backup_dir))


class OfflineViewsTestCase(TestCase):
    """Test the offline-related views"""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        
        # Create a client and log in
        self.client = Client()
        self.client.login(username="testuser", password="password123")
        
        # Create sample data in the queue
        for status in ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]:
            OfflineQueue.objects.create(
                operation_type="CREATE",
                model_name="Grade",
                object_id="",
                user=self.user,
                data={"status": status},
                status=status
            )
    
    @patch("belletin.offline.OfflineSynchronizer.process_queue")
    def test_synchronize_endpoint(self, mock_process_queue):
        """Test the synchronize_offline_data endpoint"""
        # Configure the mock to return some stats
        mock_process_queue.return_value = (1, 1, 2)
        
        # Make a POST request to the synchronize endpoint
        response = self.client.post(
            reverse("synchronize_offline_data"),
            {},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        # Check that the response is JSON with the right stats
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["processed"], 1)
        self.assertEqual(data["failed"], 1)
        self.assertEqual(data["remaining"], 2)
    
    def test_queue_status_view(self):
        """Test the offline queue status view"""
        # Make a GET request to the queue status view
        response = self.client.get(reverse("offline_queue_status"))
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that the context contains the right stats
        self.assertEqual(response.context["stats"]["pending"], 1)
        self.assertEqual(response.context["stats"]["processing"], 1)
        self.assertEqual(response.context["stats"]["completed"], 1)
        self.assertEqual(response.context["stats"]["failed"], 1)
        self.assertEqual(response.context["stats"]["total"], 4)


class UIOfflineIntegrationTestCase(TestCase):
    """Test the UI integration with offline functionality"""
    
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        
        # Create a client and log in
        self.client = Client()
        self.client.login(username="testuser", password="password123")
        
        # Setup academic structure
        self.academic_year = AcademicYear.objects.create(
            name="2024-2025", 
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_current=True
        )
        
        self.faculty = Faculty.objects.create(name="Sciences")
        self.department = Department.objects.create(name="Informatique", faculty=self.faculty)
        self.promotion = Promotion.objects.create(
            level="L1",
            department=self.department,
            academic_year=self.academic_year
        )
        
        # Create professor
        self.professor_user = User.objects.create_user(
            username="prof", email="prof@test.com", password="prof123"
        )
        self.professor = Professor.objects.create(
            user=self.professor_user,
            department=self.department
        )
        
        # Create student
        self.student_user = User.objects.create_user(
            username="student", email="student@test.com", password="student123"
        )
        self.student = Student.objects.create(
            user=self.student_user,
            matricule="STD001",
            promotion=self.promotion,
            current_academic_year=self.academic_year
        )
        
        # Create course
        self.ue = UE.objects.create(
            code="INF101",
            title="Programming",
            credits=6,
            semester=1,
            promotion=self.promotion
        )
        self.course = Course.objects.create(
            ue=self.ue,
            professor=self.professor,
            academic_year=self.academic_year
        )
    
    def test_offline_form_submission(self):
        """Test form submission in offline mode"""
        # Login as professor
        self.client.login(username="prof", password="prof123")
        
        # Submit a grade form with offline mode
        response = self.client.post(
            reverse("quick_grade", args=[self.course.id]),
            {
                "student_id": self.student.id,
                "cc": 15.0,
                "mc": 17.0,
                "offline_mode": "true"
            }
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that an entry was created in the offline queue
        queue_items = OfflineQueue.objects.filter(
            user=self.professor_user,
            model_name="Grade"
        )
        self.assertEqual(queue_items.count(), 1)
        
        # Check the queue item data
        queue_item = queue_items.first()
        self.assertEqual(queue_item.operation_type, "CREATE")
        self.assertEqual(queue_item.data["cc"], 15.0)
        self.assertEqual(queue_item.data["mc"], 17.0)
        
        # Check that no actual grade was created yet
        self.assertEqual(Grade.objects.count(), 0)
    
    @patch("belletin.offline.OfflineSynchronizer.process_queue")
    def test_synchronization_on_reconnect(self, mock_process_queue):
        """Test synchronization when coming back online"""
        # Configure the mock to return some stats
        mock_process_queue.return_value = (1, 0, 0)
        
        # Create a queue item
        OfflineQueue.objects.create(
            operation_type="CREATE",
            model_name="Grade",
            object_id="",
            user=self.user,
            data={
                "student_id": self.student.id,
                "ue_id": self.ue.id,
                "cc": 15.0,
                "mc": 17.0
            },
            status="PENDING"
        )
        
        # Simulate reconnection by calling the synchronize endpoint
        response = self.client.post(
            reverse("synchronize_offline_data"),
            {},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        
        # Check that the response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that process_queue was called
        mock_process_queue.assert_called_once()


class CronBackupTestCase(TestCase):
    """Test the cron backup functionality"""
    
    @patch("subprocess.run")
    def test_cron_backup_script(self, mock_run):
        """Test the cron_backup.py script execution"""
        # Since we can't easily test the script directly,
        # we'll just check it exists and has the right permissions
        script_path = os.path.join(os.getcwd(), "cron_backup.py")
        self.assertTrue(os.path.exists(script_path))
        
        # Check it's executable (on Unix systems)
        if os.name != 'nt':  # Skip on Windows
            self.assertTrue(os.access(script_path, os.X_OK)) 