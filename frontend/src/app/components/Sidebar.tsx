import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { BookOpen, ChevronLeft, ChevronRight, FileUp, GitBranch, Library, ListIcon, MessageCircle, Plus, Settings as SettingsIcon } from "lucide-react";

import {
  createAppSession,
  getAppSessionOpenRoute,
  getProfilingRoute,
  listAppSessions,
  selectAppSession,
  type AppSessionItem,
} from "../end-points/appSessionsApi";
import {
  deleteHL7Session,
  listHL7Sessions,
  type HL7SessionListItem,
} from "../end-points/hl7Api";
import { getCurrentAppSessionId, onSessionChanged, emitNewSessionLoading } from "../utils/appSessionStorage";
import { useChat } from "../contexts/ChatContext";
import { sttmNav } from "../utils/sttmRoutes";
import {
  interchangeAnalysesSectionTitle,
  interchangeMappingActionLabel,
  interchangeMappingActionTitle,
  interchangeMappingPath,
  interchangeOpenActionLabel,
  interchangeSessionLabel,
} from "../utils/interchangeSessionLabel";

const links = [
  { to: sttmNav("/upload"), icon: FileUp, title: "New Profiling" },
  { to: sttmNav("/mapping"), icon: GitBranch, title: "Mapping" },
  { to: sttmNav("/mappings-library"), icon: Library, title: "Mappings Library" },
  { to: sttmNav("/sessions"), icon: ListIcon, title: "Sessions" },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export default function Sidebar({ isCollapsed, onToggleCollapse }: SidebarProps) {
  const { isChatOpen, setIsChatOpen } = useChat();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<AppSessionItem[]>([]);
  const [hl7Sessions, setHl7Sessions] = useState<HL7SessionListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [newSessionLoading, setNewSessionLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(getCurrentAppSessionId());

  const refreshSessions = async () => {
    try {
      const data = await listAppSessions();
      setSessions(data.slice(0, 10));
      setLoadError(null);
      setCurrentSessionId(getCurrentAppSessionId());
      const linkedIds = new Set(
        data.map((s) => s.current_hl7_session_id).filter(Boolean) as string[]
      );
      listHL7Sessions()
        .then((hl7) => {
          setHl7Sessions(hl7.filter((h) => !linkedIds.has(h.hl7_session_id)).slice(0, 5));
        })
        .catch(() => setHl7Sessions([]));
    } catch (error) {
      console.error("Failed to load app sessions:", error);
      setLoadError(error instanceof Error ? error.message : "Failed to load sessions");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshSessions();
    return onSessionChanged(() => {
      setCurrentSessionId(getCurrentAppSessionId());
      refreshSessions();
    });
  }, []);

  const handleCreateSession = async () => {
    setNewSessionLoading(true);
    emitNewSessionLoading(true);
    try {
      await createAppSession(undefined, "sess");
      navigate(sttmNav("/upload"));
    } catch (error) {
      console.error("Failed to create session:", error);
    } finally {
      setNewSessionLoading(false);
      emitNewSessionLoading(false);
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    try {
      const detail = await selectAppSession(sessionId);
      setCurrentSessionId(sessionId);
      navigate(sttmNav(getAppSessionOpenRoute(detail)));
    } catch (error) {
      console.error("Failed to select session:", error);
    }
  };

  const handleOpenWorkflow = async (
    sessionId: string,
    route: "profiling" | "mapping" | "extract",
    event?: React.MouseEvent<HTMLButtonElement>,
  ) => {
    event?.stopPropagation();
    try {
      const detail = await selectAppSession(sessionId);
      setCurrentSessionId(sessionId);
      let target = "/extract";
      if (route === "mapping") target = "/mapping?resume=1";
      else if (route === "profiling") target = getProfilingRoute(detail);
      navigate(sttmNav(target));
    } catch (error) {
      console.error(`Failed to open ${route}:`, error);
    }
  };

  const linkClasses = ({ isActive }: { isActive: boolean }) =>
    [
      "flex items-center transition-colors text-sm border-l-[3px]",
      isCollapsed ? "justify-center px-2 py-2 border-l-0" : "gap-3 px-3 py-2",
      isActive
        ? "bg-[var(--ust-light-gray)] text-[var(--ust-soft-black)] border-l-[var(--ust-light-teal)] font-semibold"
        : "text-[var(--ust-body-text)] border-l-transparent hover:bg-[var(--ust-light-gray)] hover:text-[var(--ust-dark-teal)]",
    ].join(" ");

  const actionChip =
    "border border-[var(--ust-light-teal)] text-[var(--ust-dark-teal)] px-2 py-1 text-[10px] font-bold hover:bg-[var(--ust-light-gray)] transition-colors cursor-pointer whitespace-nowrap";

  return (
    <aside
      className={[
        "bg-[var(--ust-white)] h-full overflow-y-auto sidebar-scroll p-4 flex flex-col gap-3 transition-all duration-200 border-r border-[var(--ust-border-color)]",
        isCollapsed ? "w-20" : "w-72",
      ].join(" ")}
    >
      <div className="flex items-center justify-between">
        {!isCollapsed && (
          <div className="text-[var(--ust-light-teal)] text-[11px] font-bold uppercase tracking-[0.12em]">
            Menu
          </div>
        )}
        <div className="flex items-center gap-2">
          {!isCollapsed && (
            <button
              onClick={handleCreateSession}
              disabled={newSessionLoading}
              className="flex items-center justify-center gap-1 border-2 border-[var(--ust-light-teal)] bg-transparent px-2 py-1 text-xs font-bold text-[var(--ust-dark-teal)] hover:bg-[var(--ust-light-gray)] disabled:opacity-60 disabled:cursor-not-allowed transition-colors cursor-pointer"
              title="Create session"
            >
              {newSessionLoading ? (
                <div className="w-3 h-3 border-2 border-[var(--ust-light-teal)] border-t-transparent animate-spin" />
              ) : (
                <Plus size={14} />
              )}
              New Session
            </button>
          )}
          <button
            onClick={onToggleCollapse}
            className="border border-[var(--ust-border-color)] p-2 text-[var(--ust-body-text)] hover:bg-[var(--ust-light-gray)] hover:text-[var(--ust-dark-teal)] transition-colors cursor-pointer"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>
      </div>

      <nav className="flex flex-col gap-[2px]">
        {links.map(({ to, icon: Icon, title }) => (
          <NavLink key={to} to={to} className={linkClasses} title={title}>
            <Icon size={18} strokeWidth={1.5} />
            {!isCollapsed && <span>{title}</span>}
          </NavLink>
        ))}
        {!isChatOpen && (
          <button
            onClick={() => setIsChatOpen(true)}
            className={[
              "text-[var(--ust-body-text)] hover:bg-[var(--ust-light-gray)] hover:text-[var(--ust-dark-teal)] transition-colors text-sm cursor-pointer",
              isCollapsed ? "flex justify-center px-2 py-2" : "flex items-center gap-3 px-3 py-2",
            ].join(" ")}
            title="Ask about your data"
          >
            <MessageCircle size={18} strokeWidth={1.5} />
            {!isCollapsed && <span>Chat</span>}
          </button>
        )}
        <NavLink to={sttmNav("/documentation")} className={linkClasses} title="Documentation">
          <BookOpen size={18} strokeWidth={1.5} />
          {!isCollapsed && <span>Documentation</span>}
        </NavLink>
        <NavLink to={sttmNav("/settings")} className={linkClasses} title="Settings">
          <SettingsIcon size={18} strokeWidth={1.5} />
          {!isCollapsed && <span>Settings</span>}
        </NavLink>
      </nav>
      {/* Session Section   */}
      <div className="border-t border-[var(--ust-border-color)] pt-4 flex-1 min-h-0">
        <div className="flex items-center justify-between mb-3">
          {!isCollapsed && (
            <div className="text-[var(--ust-light-teal)] text-[11px] font-bold uppercase tracking-[0.12em]">
              Recent Sessions
            </div>
          )}
          <button
            onClick={() => navigate(sttmNav("/sessions"))}
            className={[
              "text-[var(--ust-dark-teal)] hover:text-[var(--ust-soft-black)] font-semibold transition-colors cursor-pointer",
              isCollapsed ? "border border-[var(--ust-border-color)] p-2 text-xs hover:bg-[var(--ust-light-gray)]" : "text-[11px]",
            ].join(" ")}
            title="Manage sessions"
          >
            {isCollapsed ? <ListIcon size={14} /> : "Manage"}
          </button>
        </div>
        {/* Session Listing */}
        <div>
          <div className="space-y-2 pb-4">
          {isLoading && <div className="text-xs text-[var(--ust-body-text)] px-2 py-1">Loading sessions...</div>}
          {!isLoading && loadError && (
            <div className="text-xs text-brand-error px-2 py-1">
              Could not load sessions. {loadError}
            </div>
          )}
          {!isLoading && !loadError && sessions.length === 0 && (
            <div className="text-xs text-[var(--ust-body-text)] px-2 py-1">No sessions yet.</div>
          )}
          {sessions.map((session) => {
            const isActive = currentSessionId === session.id;
            return (
              <div
                key={session.id}
                className={[
                  "border transition-colors border-t-[3px]",
                  isActive
                    ? "border-[var(--ust-border-color)] border-t-[var(--ust-light-teal)] bg-[var(--ust-light-gray)]"
                    : "border-[var(--ust-border-color)] border-t-transparent bg-[var(--ust-white)] hover:bg-[var(--ust-light-gray)]",
                  isCollapsed ? "px-2 py-2" : "px-3 py-2",
                ].join(" ")}
              >
                {isCollapsed ? (
                  <div className="w-full text-center">
                    <button
                      onClick={() => handleSelectSession(session.id)}
                      className="w-full cursor-pointer"
                      title={session.title}
                    >
                      <div className="text-sm text-[var(--ust-soft-black)] font-semibold truncate">{session.title.slice(0, 1).toUpperCase()}</div>
                    </button>
                    <div className="mt-1 flex flex-col gap-1 items-center">
                      {session.hl7 && (
                        <>
                          <button
                            onClick={() => navigate(sttmNav(`/hl7/${session.hl7!.hl7_session_id}`))}
                            className={actionChip}
                            title={`Open ${interchangeSessionLabel(session.hl7)}`}
                          >
                            {session.hl7.format === "x12" ? "E" : "H"}
                          </button>
                          <button
                            onClick={() =>
                              navigate(
                                sttmNav(interchangeMappingPath(session.hl7!.hl7_session_id, session.hl7!))
                              )
                            }
                            className={actionChip}
                            title={interchangeMappingActionTitle(session.hl7!)}
                          >
                            M
                          </button>
                        </>
                      )}
                      {session.current_extract_run_id && (
                        <button
                          onClick={(event) => handleOpenWorkflow(session.id, "extract", event)}
                          className={actionChip}
                          title="Open Extract"
                        >
                          E
                        </button>
                      )}
                      {session.current_profiling_run_id && (
                        <button
                          onClick={(event) => handleOpenWorkflow(session.id, "profiling", event)}
                          className={actionChip}
                          title="Open Profiling"
                        >
                          P
                        </button>
                      )}
                      {session.current_mapping_run_id && (
                        <button
                          onClick={(event) => handleOpenWorkflow(session.id, "mapping", event)}
                          className={actionChip}
                          title="Open Mapping"
                        >
                          M
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-1.5 min-w-0">
                      <button
                        onClick={() => handleSelectSession(session.id)}
                        className="min-w-0 flex-1 text-left cursor-pointer"
                      >
                        <div className="text-xs text-[var(--ust-soft-black)] font-medium truncate">{session.title}</div>
                      </button>
                      <div className="flex shrink-0 items-center gap-1">
                        {session.id.startsWith("extract_") ? (
                          session.current_extract_run_id ? (
                            <button
                              onClick={(event) => handleOpenWorkflow(session.id, "extract", event)}
                              className={actionChip}
                            >
                              Extract
                            </button>
                          ) : (
                            <span className="border border-[var(--ust-border-color)] px-2 py-1 text-[10px] font-medium text-[var(--ust-body-text)] whitespace-nowrap">
                              No extract
                            </span>
                          )
                        ) : session.hl7 ? (
                          <>
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                navigate(sttmNav(`/hl7/${session.hl7!.hl7_session_id}`));
                              }}
                              className={actionChip}
                              title={`Open ${interchangeSessionLabel(session.hl7)}`}
                            >
                              {interchangeOpenActionLabel(session.hl7)}
                            </button>
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                navigate(
                                  sttmNav(
                                    interchangeMappingPath(session.hl7!.hl7_session_id, session.hl7!)
                                  )
                                );
                              }}
                              className={actionChip}
                              title={interchangeMappingActionTitle(session.hl7!)}
                            >
                              {interchangeMappingActionLabel(session.hl7!)}
                            </button>
                          </>
                        ) : (
                          <>
                            {session.current_profiling_run_id ? (
                              <button
                                onClick={(event) => handleOpenWorkflow(session.id, "profiling", event)}
                                className={actionChip}
                              >
                                Profiling
                              </button>
                            ) : (
                              <span className="border border-[var(--ust-border-color)] px-2 py-1 text-[10px] font-medium text-[var(--ust-body-text)] whitespace-nowrap">
                                No profiling
                              </span>
                            )}
                            {session.current_mapping_run_id ? (
                              <button
                                onClick={(event) => handleOpenWorkflow(session.id, "mapping", event)}
                                className={actionChip}
                              >
                                Mapping
                              </button>
                            ) : (
                              <span className="border border-[var(--ust-border-color)] px-2 py-1 text-[10px] font-medium text-[var(--ust-body-text)] whitespace-nowrap">
                                No mapping
                              </span>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            );
          })}
          {!isLoading && hl7Sessions.length > 0 && !isCollapsed && (
            <div className="pt-2 mt-2 border-t border-[var(--ust-border-color)]">
              <div className="text-[var(--ust-light-teal)] text-[10px] font-bold uppercase tracking-[0.12em] px-1 mb-2">
                {interchangeAnalysesSectionTitle(hl7Sessions)}
              </div>
              {hl7Sessions.map((hl7) => (
                <div
                  key={hl7.hl7_session_id}
                  className="border border-[var(--ust-border-color)] border-t-[3px] border-t-[var(--ust-light-teal)] bg-[var(--ust-white)] hover:bg-[var(--ust-light-gray)] px-3 py-2 mb-2"
                >
                  <div className="text-xs text-[var(--ust-soft-black)] font-medium truncate">
                    {interchangeSessionLabel(hl7)} · {hl7.hl7_session_id.slice(0, 8)}
                  </div>
                  <div className="flex items-center gap-1 mt-1">
                    <button
                      onClick={() => navigate(sttmNav(`/hl7/${hl7.hl7_session_id}`))}
                      className={actionChip}
                    >
                      {interchangeOpenActionLabel(hl7)}
                    </button>
                    <button
                      onClick={() =>
                        navigate(sttmNav(interchangeMappingPath(hl7.hl7_session_id, hl7)))
                      }
                      className={actionChip}
                      title={interchangeMappingActionTitle(hl7)}
                    >
                      {interchangeMappingActionLabel(hl7)}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          </div>
        </div>
      </div>
    </aside>
  );
}