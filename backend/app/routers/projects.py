from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_project_for_member
from ..models import Project, ProjectMember, Sprint, Story, User
from ..schemas.auth import UserRead
from ..schemas.projects import ProjectCreate, ProjectRead, ProjectSummary, ProjectUpdate, TeamMemberAdd
from ..schemas.trash import DeleteResult
from ..services.github_links import normalize_repo_url
from ..services.soft_delete import delete_project as soft_delete_project
from ..services.sprints import serialize_sprints, sprint_status

router = APIRouter(prefix="/api/projects", tags=["projects"])

STATUSES = ["backlog", "selected", "in_progress", "blocked", "done"]


def project_read(db: Session, project: Project) -> ProjectRead:
    members = (
        db.query(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project.id)
        .order_by(User.name)
        .all()
    )
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        github_repo_url=project.github_repo_url,
        created_at=project.created_at,
        members=[UserRead.model_validate(member) for member in members],
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ProjectRead]:
    projects = (
        db.query(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [project_read(db, project) for project in projects]


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProjectRead:
    project = Project(name=payload.name.strip(), description=payload.description, owner_id=user.id)
    db.add(project)
    db.flush()
    for member_id in dict.fromkeys([user.id, *payload.team_member_ids]):
        if not db.get(User, member_id):
            raise HTTPException(status_code=400, detail=f"Unknown team member: {member_id}")
        db.add(ProjectMember(project_id=project.id, user_id=member_id, role="member"))
    db.commit()
    db.refresh(project)
    return project_read(db, project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProjectRead:
    return project_read(db, get_project_for_member(db, project_id, user))


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_for_member(db, project_id, user)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name") is not None:
        project.name = data["name"].strip()
    if data.get("description") is not None:
        project.description = data["description"]
    if "github_repo_url" in data:
        project.github_repo_url = normalize_repo_url(data["github_repo_url"])
    db.commit()
    db.refresh(project)
    return project_read(db, project)


@router.delete("/{project_id}", response_model=DeleteResult)
def delete_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DeleteResult:
    project = get_project_for_member(db, project_id, user)
    batch = soft_delete_project(db, project, user)
    db.commit()
    return DeleteResult(batch_id=batch.id, counts=batch.counts)


@router.post("/{project_id}/team", response_model=ProjectRead)
def add_team_member(
    project_id: str,
    payload: TeamMemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_for_member(db, project_id, user)
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=400, detail="Unknown user")
    if not db.query(ProjectMember).filter_by(project_id=project.id, user_id=payload.user_id).first():
        db.add(ProjectMember(project_id=project.id, user_id=payload.user_id, role="member"))
        db.commit()
    return project_read(db, project)


@router.delete("/{project_id}/team/{user_id}", response_model=ProjectRead)
def remove_team_member(
    project_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectRead:
    project = get_project_for_member(db, project_id, user)
    membership = db.query(ProjectMember).filter_by(project_id=project.id, user_id=user_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="That user isn't a member of this project")
    if db.query(ProjectMember).filter_by(project_id=project.id).count() <= 1:
        raise HTTPException(status_code=400, detail="A project needs at least one member")
    # PERM-3: their stories become unassigned; comments and history stay attributed to them.
    stories = (
        db.query(Story)
        .execution_options(include_deleted=True)
        .filter(Story.project_id == project.id, Story.assignee_id == user_id)
        .all()
    )
    for story in stories:
        story.assignee_id = None
    db.delete(membership)
    db.commit()
    return project_read(db, project)


@router.get("/{project_id}/summary", response_model=ProjectSummary)
def project_summary(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ProjectSummary:
    project = get_project_for_member(db, project_id, user)
    stories = db.query(Story).filter(Story.project_id == project.id).all()
    counts = Counter(story.status for story in stories)
    sprints = db.query(Sprint).filter(Sprint.project_id == project.id).order_by(Sprint.start_date).all()
    active = [sprint for sprint in sprints if sprint_status(sprint) == "active"]
    return ProjectSummary(
        counts={status: counts.get(status, 0) for status in STATUSES},
        total_stories=len(stories),
        active_sprints=serialize_sprints(db, active),
    )
