import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarRange,
  ClipboardList,
  Columns3,
  ExternalLink,
  LogOut,
  MessageSquare,
  Network,
  RefreshCw,
  Settings,
  Trash2,
} from "lucide-react";
import { authApi } from "./api/auth";
import { onUnauthorized } from "./api/client";
import { projectsApi } from "./api/projects";
import { sprintsApi } from "./api/sprints";
import { useAsync } from "./api/useAsync";
import { EmptyState } from "./components/EmptyState";
import { ErrorBanner } from "./components/ErrorBanner";
import { PanelTitle } from "./components/PanelTitle";
import { Spinner } from "./components/Spinner";
import { ToastProvider } from "./components/Toast";
import { APP_NAME } from "./constants";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { BoardView } from "./features/board/BoardView";
import { DiscussionView } from "./features/discussion/DiscussionView";
import { PlanningView } from "./features/planning/PlanningView";
import { ProjectForm } from "./features/settings/ProjectForm";
import { SettingsView } from "./features/settings/SettingsView";
import { DeletedProjects } from "./features/trash/DeletedProjects";
import { TrashView } from "./features/trash/TrashView";
import { WorkspaceContext, defaultSprint, storage } from "./workspace";

// React Flow is large, so the graph loads only when its tab opens.
const GraphView = lazy(() => import("./features/graph/GraphView").then((module) => ({ default: module.GraphView })));

const TABS = [
  ["board", "Board", Columns3],
  ["planning", "Planning", CalendarRange],
  ["graph", "Graph", Network],
  ["discussion", "Discussion", MessageSquare],
  ["trash", "Trash", Trash2],
  ["settings", "Settings", Settings],
];

export function App() {
  const [user, setUser] = useState(null);
  const [checked, setChecked] = useState(false);
  const [screen, setScreen] = useState("login");

  useEffect(() => {
    onUnauthorized(() => setUser(null));
    authApi
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecked(true));
  }, []);

  if (!checked) {
    return (
      <main className="auth-shell">
        <Spinner />
      </main>
    );
  }
  if (!user) {
    return screen === "login" ? (
      <LoginPage onAuthenticated={setUser} onSwitch={() => setScreen("register")} />
    ) : (
      <RegisterPage onAuthenticated={setUser} onSwitch={() => setScreen("login")} />
    );
  }
  return (
    <ToastProvider>
      <Workspace
        user={user}
        onLogout={async () => {
          await authApi.logout().catch(() => {});
          setUser(null);
          setScreen("login");
        }}
      />
    </ToastProvider>
  );
}

function Workspace({ user, onLogout }) {
  const projects = useAsync(() => projectsApi.list(), []);
  const users = useAsync(() => authApi.users(), []);
  const [projectId, setProjectId] = useState(() => storage.get("dbpm-project") || "");
  const [view, setView] = useState(() => {
    const saved = storage.get("dbpm-view");
    return TABS.some(([key]) => key === saved) ? saved : "board";
  });
  const [sprintId, setSprintId] = useState("");
  const [storyId, setStoryId] = useState(null);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);

  useEffect(() => {
    if (projects.data && !projects.data.some((item) => item.id === projectId)) {
      setProjectId(projects.data[0]?.id || "");
    }
  }, [projects.data, projectId]);
  useEffect(() => storage.set("dbpm-project", projectId), [projectId]);
  useEffect(() => storage.set("dbpm-view", view), [view]);
  useEffect(() => setStoryId(null), [projectId]);

  const project = useAsync(() => (projectId ? projectsApi.get(projectId) : Promise.resolve(null)), [projectId]);
  const sprints = useAsync(() => (projectId ? sprintsApi.list(projectId) : Promise.resolve([])), [projectId]);

  useEffect(() => {
    const list = sprints.data || [];
    if (list.length && list[0].project_id !== projectId) return;
    if (!list.some((sprint) => sprint.id === sprintId)) {
      const saved = storage.get(`dbpm-sprint-${projectId}`);
      setSprintId(list.some((sprint) => sprint.id === saved) ? saved : defaultSprint(list)?.id || "");
    }
  }, [sprints.data, sprintId, projectId]);

  const selectSprint = useCallback(
    (id) => {
      setSprintId(id);
      storage.set(`dbpm-sprint-${projectId}`, id);
    },
    [projectId],
  );

  const reloadSprints = sprints.reload;
  const reloadProject = project.reload;
  const changed = useCallback(async () => {
    await Promise.all([reloadSprints(), reloadProject()]);
    setVersion((value) => value + 1);
  }, [reloadSprints, reloadProject]);

  const refreshAll = useCallback(async () => {
    await Promise.all([projects.reload(), users.reload()]);
    await changed();
  }, [projects, users, changed]);

  const sprintList = useMemo(() => (sprints.data || []).filter((sprint) => sprint.project_id === projectId), [sprints.data, projectId]);
  const selectedSprint = sprintList.find((sprint) => sprint.id === sprintId) || null;
  const currentProject = project.data && project.data.id === projectId ? project.data : null;

  const context = {
    user,
    users: users.data || [],
    project: currentProject,
    members: currentProject?.members || [],
    sprints: sprintList,
    selectedSprint,
    selectSprint,
    version,
    changed,
    reloadProjects: projects.reload,
    storyId,
    openStory: setStoryId,
    closeStory: () => setStoryId(null),
    setError,
  };

  return (
    <WorkspaceContext.Provider value={context}>
      <main className="app-shell">
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">
              <Columns3 size={22} />
            </div>
            <div>
              <h1>{APP_NAME}</h1>
              <p>Project planning, sprint execution, and reporting.</p>
            </div>
          </div>

          <div className="current-user">
            <div>
              <strong>{user.name}</strong>
              <span>@{user.username}</span>
            </div>
            <button className="ghost-button" onClick={onLogout} title="Log out">
              <LogOut size={16} /> Log out
            </button>
          </div>

          <section className="panel">
            <PanelTitle icon={<ClipboardList size={16} />} title="Projects" />
            <div className="project-list">
              {(projects.data || []).map((item) => (
                <button
                  key={item.id}
                  className={item.id === projectId ? "project-button active" : "project-button"}
                  onClick={() => setProjectId(item.id)}
                >
                  <strong>{item.name}</strong>
                  <span>{item.members.length} members</span>
                </button>
              ))}
              {projects.loading && !projects.data && <Spinner />}
            </div>
            <ProjectForm
              users={(users.data || []).filter((item) => item.id !== user.id)}
              onCreate={async (payload) => {
                const created = await projectsApi.create(payload);
                await projects.reload();
                setProjectId(created.id);
              }}
            />
            <button className="link-button sidebar-link" onClick={() => setShowDeleted(true)}>
              <Trash2 size={14} /> Deleted projects
            </button>
          </section>
        </aside>

        <section className="workspace">
          <header className="topbar">
            <div>
              <p className="eyebrow">Active Workspace</p>
              <h2>{currentProject?.name || (projects.data?.length ? "Loading…" : "No project selected")}</h2>
              <p>
                {currentProject?.description || (currentProject ? "" : "Create or select a project to begin.")}
                {currentProject?.github_repo_url && (
                  <a className="repo-link" href={currentProject.github_repo_url} target="_blank" rel="noreferrer">
                    <ExternalLink size={13} /> {currentProject.github_repo_url.replace("https://github.com/", "")}
                  </a>
                )}
              </p>
            </div>
            <button className="icon-button" onClick={() => refreshAll().catch((err) => setError(err.message))} title="Refresh">
              <RefreshCw size={18} />
            </button>
          </header>

          <ErrorBanner message={error || projects.error || project.error || sprints.error} onDismiss={() => setError("")} />

          {currentProject ? (
            <>
              <nav className="tab-bar" aria-label="Views">
                {TABS.map(([key, label, Icon]) => (
                  <button key={key} className={view === key ? "tab active" : "tab"} onClick={() => setView(key)} aria-current={view === key}>
                    <Icon size={15} /> {label}
                  </button>
                ))}
              </nav>
              {view === "board" && <BoardView />}
              {view === "planning" && <PlanningView />}
              {view === "graph" && (
                <Suspense fallback={<Spinner />}>
                  <GraphView />
                </Suspense>
              )}
              {view === "discussion" && <DiscussionView />}
              {view === "trash" && <TrashView />}
              {view === "settings" && (
                <SettingsView
                  onProjectDeleted={async () => {
                    await projects.reload();
                    setProjectId("");
                  }}
                />
              )}
            </>
          ) : (
            !projects.loading &&
            !projects.data?.length && (
              <EmptyState
                title="No projects yet"
                body="Create a project in the sidebar, or ask a teammate to add you to theirs."
              />
            )
          )}
        </section>
      </main>
      {showDeleted && (
        <DeletedProjects
          onClose={() => setShowDeleted(false)}
          onRestored={async (restoredId) => {
            await projects.reload();
            setProjectId(restoredId);
          }}
        />
      )}
    </WorkspaceContext.Provider>
  );
}
