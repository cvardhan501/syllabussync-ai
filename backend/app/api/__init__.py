from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.syllabus import router as syllabus_router
from app.api.resources import router as resources_router
from app.api.study_plan import router as study_plan_router
from app.api.diagnostics import router as diagnostics_router
from app.api.courses import router as courses_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(syllabus_router)
api_router.include_router(resources_router)
api_router.include_router(study_plan_router)
api_router.include_router(diagnostics_router)
api_router.include_router(courses_router)



