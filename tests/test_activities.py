"""Test suite for the activities API endpoints"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original activities
    original_activities = copy.deepcopy(activities)
    
    # Reset activities to their initial state
    activities.clear()
    activities.update(copy.deepcopy(original_activities))
    
    yield
    
    # Cleanup: reset after test
    activities.clear()
    activities.update(copy.deepcopy(original_activities))


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Should return all activities with their details"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) == 9  # 9 activities total

    def test_get_activities_includes_correct_fields(self, client, reset_activities):
        """Should include all required fields for each activity"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity

    def test_get_activities_participants_is_list(self, client, reset_activities):
        """Should return participants as a list"""
        response = client.get("/activities")
        data = response.json()
        
        assert isinstance(data["Chess Club"]["participants"], list)
        assert len(data["Chess Club"]["participants"]) == 2


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successfully_adds_participant(self, client, reset_activities):
        """Should add a new participant to an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Signed up newstudent@mergington.edu for Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
        assert len(activities_data["Chess Club"]["participants"]) == 3

    def test_signup_with_invalid_activity_returns_404(self, client, reset_activities):
        """Should return 404 for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_with_duplicate_email_returns_400(self, client, reset_activities):
        """Should return 400 if student is already signed up"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_with_full_activity_returns_400(self, client, reset_activities):
        """Should return 400 if activity is at max capacity"""
        # Find an activity near capacity
        chess_club = activities["Chess Club"]
        original_max = chess_club["max_participants"]
        
        # Set max to current participant count
        chess_club["max_participants"] = len(chess_club["participants"])
        
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 400
        assert "Activity is full" in response.json()["detail"]
        
        # Cleanup
        chess_club["max_participants"] = original_max

    def test_signup_with_empty_email_returns_400(self, client, reset_activities):
        """Should return 400 if email is empty"""
        response = client.post("/activities/Chess Club/signup?email=")
        assert response.status_code == 400
        assert "required" in response.json()["detail"]

    def test_signup_with_invalid_email_format_returns_400(self, client, reset_activities):
        """Should return 400 for invalid email format"""
        response = client.post(
            "/activities/Chess Club/signup?email=invalidemail"
        )
        assert response.status_code == 400
        assert "Invalid email format" in response.json()["detail"]

    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Should handle emails with special characters that are valid"""
        response = client.post(
            "/activities/Chess Club/signup?email=student+alias@mergington.edu"
        )
        assert response.status_code == 200

    def test_signup_multiple_different_students(self, client, reset_activities):
        """Should allow multiple different students to sign up"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu",
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/Programming Class/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all were added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Programming Class"]["participants"]
        for email in emails:
            assert email in participants


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/remove endpoint"""

    def test_remove_participant_successfully(self, client, reset_activities):
        """Should remove a participant from an activity"""
        # Verify participant exists
        response = client.get("/activities")
        initial_participants = response.json()["Chess Club"]["participants"]
        assert "michael@mergington.edu" in initial_participants
        
        # Remove participant
        response = client.delete(
            "/activities/Chess Club/remove?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "Removed michael@mergington.edu" in response.json()["message"]
        
        # Verify participant was removed
        response = client.get("/activities")
        remaining_participants = response.json()["Chess Club"]["participants"]
        assert "michael@mergington.edu" not in remaining_participants
        assert len(remaining_participants) == len(initial_participants) - 1

    def test_remove_from_invalid_activity_returns_404(self, client, reset_activities):
        """Should return 404 for non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/remove?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_remove_nonexistent_participant_returns_400(self, client, reset_activities):
        """Should return 400 if student is not signed up"""
        response = client.delete(
            "/activities/Chess Club/remove?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_remove_with_empty_email_returns_400(self, client, reset_activities):
        """Should return 400 if email is empty"""
        response = client.delete("/activities/Chess Club/remove?email=")
        assert response.status_code == 400
        assert "required" in response.json()["detail"]

    def test_remove_multiple_participants(self, client, reset_activities):
        """Should allow removing multiple participants from same activity"""
        participants_to_remove = [
            "michael@mergington.edu",
            "daniel@mergington.edu",
        ]
        
        for email in participants_to_remove:
            response = client.delete(
                f"/activities/Chess Club/remove?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all were removed
        response = client.get("/activities")
        remaining = response.json()["Chess Club"]["participants"]
        for email in participants_to_remove:
            assert email not in remaining
        assert len(remaining) == 0

    def test_remove_and_re_signup_same_participant(self, client, reset_activities):
        """Should allow participant to re-sign up after removal"""
        email = "michael@mergington.edu"
        
        # Remove participant
        response = client.delete(
            f"/activities/Chess Club/remove?email={email}"
        )
        assert response.status_code == 200
        
        # Re-sign up
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify they're signed up
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]


class TestActivityIntegration:
    """Integration tests combining multiple endpoints"""

    def test_full_signup_flow(self, client, reset_activities):
        """Test complete signup workflow"""
        email = "testuser@mergington.edu"
        activity = "Art Studio"
        
        # Get initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count + 1

    def test_signup_remove_signup_flow(self, client, reset_activities):
        """Test signup, removal, and re-signup workflow"""
        email = "testuser@mergington.edu"
        activity = "Drama Club"
        
        # First signup
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Remove
        response = client.delete(
            f"/activities/{activity}/remove?email={email}"
        )
        assert response.status_code == 200
        
        # Re-signup
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify final state
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
