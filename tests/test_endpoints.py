import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, UploadFile, status
from app.routers.auth import validate_pdf_file
from app.services.course_public_service import CoursePublicService

# 1. Test PDF stream validation rules
def test_validate_pdf_file_wrong_extension():
    document = MagicMock(spec=UploadFile)
    document.filename = "letter.docx"
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_file(document)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "must be a PDF" in exc_info.value.detail

def test_validate_pdf_file_exceeds_size():
    document = MagicMock(spec=UploadFile)
    document.filename = "letter.pdf"
    document.file = MagicMock()
    document.file.read.return_value = b"%PDF"
    document.file.tell.return_value = 6 * 1024 * 1024  # 6 MB
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_file(document)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds the strict 5MB limit" in exc_info.value.detail

def test_validate_pdf_file_wrong_header():
    document = MagicMock(spec=UploadFile)
    document.filename = "letter.pdf"
    document.file = MagicMock()
    document.file.read.return_value = b"DOCX"
    document.file.tell.return_value = 1 * 1024 * 1024  # 1 MB
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_file(document)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not contain a valid PDF signature" in exc_info.value.detail

def test_validate_pdf_file_valid():
    document = MagicMock(spec=UploadFile)
    document.filename = "letter.pdf"
    document.file = MagicMock()
    document.file.read.return_value = b"%PDF"
    document.file.tell.return_value = 1 * 1024 * 1024  # 1 MB
    # Should not raise exception
    validate_pdf_file(document)

# 2. Test Dynamic Anonymity and Course Public Details
@pytest.mark.asyncio
async def test_course_public_service_anonymity_visible():
    db = AsyncMock()
    course_id = uuid.uuid4()
    
    mock_teacher = MagicMock()
    mock_teacher.email = "instructor@example.edu"
    mock_teacher.preferences = {"full_name": "Dr. Sarah Al-Jamil"}
    
    mock_course = MagicMock()
    mock_course.id = course_id
    mock_course.title = "Database Systems"
    mock_course.code = "CS101"
    mock_course.major = "Computer Science"
    mock_course.description = "Database systems and schemas"
    mock_course.price = 99.99
    mock_course.rating_avg = 4.5
    mock_course.teacher_profile_visibility = True
    mock_course.teacher = mock_teacher
    mock_course.lessons = [MagicMock(order_index=1, video_url="http://example.com/v1")]
    mock_course.summaries = []
    mock_course.virtual_classes = []

    with patch("app.repositories.course_repository.CourseRepository.get_course_details", return_value=mock_course):
        details = await CoursePublicService.get_course_details(db, str(course_id))
        assert details is not None
        assert details["teacher_name"] == "Dr. Sarah Al-Jamil"
        assert details["lessons_count"] == 1
        assert details["summaries_count"] == 0

@pytest.mark.asyncio
async def test_course_public_service_anonymity_hidden():
    db = AsyncMock()
    course_id = uuid.uuid4()
    
    mock_teacher = MagicMock()
    mock_teacher.email = "instructor@example.edu"
    mock_teacher.preferences = {"full_name": "Dr. Sarah Al-Jamil"}
    
    mock_course = MagicMock()
    mock_course.id = course_id
    mock_course.title = "Database Systems"
    mock_course.code = "CS101"
    mock_course.major = "Computer Science"
    mock_course.description = "Database systems and schemas"
    mock_course.price = 99.99
    mock_course.rating_avg = 4.5
    mock_course.teacher_profile_visibility = False
    mock_course.teacher = mock_teacher
    mock_course.lessons = []
    mock_course.summaries = []
    mock_course.virtual_classes = []

    with patch("app.repositories.course_repository.CourseRepository.get_course_details", return_value=mock_course):
        details = await CoursePublicService.get_course_details(db, str(course_id))
        assert details is not None
        assert details["teacher_name"] == "Anonymous Instructor"
