import React, { useState, useEffect, useRef } from 'react';
import useEventCallback from '@restart/hooks/useEventCallback';
import {
  Navbar,
  Container,
  Row,
  Col,
  Card,
  Button,
  Form,
  Table,
  Badge,
  Modal,
  Alert,
  Nav,
  Spinner,
} from 'react-bootstrap';
import {
  Plus,
  Star,
  ExternalLink,
  Trash2,
  Edit3,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  ChevronDown,
  Lock,
  Unlock,
  Shield,
  Users,
  KeyRound,
  LogOut,
  Database,
  UserPlus,
  Home,
  FolderOpen,
  Sparkles,
  Settings,
} from 'lucide-react';
import { api } from './api';
import HomeDashboard from './HomeDashboard';
import AccountProfileModal from './AccountProfileModal';
import ProjectOverviewExtras from './ProjectOverviewExtras';
import EvidenceDetailModal from './EvidenceDetailModal';
import { MitreTacticsSelect, MitreTechniquesSelect } from './MitreMultiSelect';

const STATUS_LABELS = {
  OPEN: 'Open / Triage',
  INVESTIGATING: 'Investigating',
  CONTAINED: 'Contained',
  ARCHIVED: 'Archived / Closed',
};

const ROLE_LABELS = {
  SUPER_ADMIN: 'Super Admin',
  ADMIN: 'Admin',
  ANALYST: 'Analyst',
  EXECUTIVE: 'Executive',
};

const ROLE_BADGE_BG = {
  SUPER_ADMIN: 'danger',
  ADMIN: 'primary',
  ANALYST: 'info',
  EXECUTIVE: 'secondary',
};

const DEFAULT_DEMO_SCENARIOS = [
  {
    id: 'expanse',
    theme: 'The Expanse',
    label: 'The Expanse — VPN Intrusion, AD Compromise & Exfiltration',
  },
  {
    id: 'star_trek',
    theme: 'Star Trek',
    label: 'Star Trek — Website Compromise & Web Shell Deployment',
  },
  {
    id: 'matrix',
    theme: 'The Matrix',
    label: 'The Matrix — ClickFix User Compromise to DC Takeover',
  },
  {
    id: 'star_wars',
    theme: 'Star Wars',
    label: 'Star Wars — MitM Phishing, Spam Wave & Multi-Account Takeover',
  },
];

const EMPTY_PROJECT_FORM = {
  title: '',
  customer_name: '',
  customer_id: '',
  ticket_id: '',
  ticket_link: '',
  summary: '',
  action_plan: '',
  key_customer_contacts: '',
  key_assets_affected: '',
  key_users_affected: '',
  key_malicious_indicators: '',
  external_research_link: '',
  external_research_summary: '',
  status: 'INVESTIGATING',
  lead_analyst: '',
};

const EMPTY_EVIDENCE_FORM = {
  evidence_type: 'ATOMIC',
  analyst_name: '',
  timestamp: '',
  end_timestamp: '',
  summary: '',
  affected_asset: '',
  affected_user: '',
  user_created_by_attacker: false,
  malicious_hosts_ips: '',
  commands_run: '',
  mitre_tactic: '',
  mitre_technique: '',
  related_log_link: '',
  search_result_link: '',
  search_query_link: '',
  notes: '',
  is_key_evidence: false,
};

const EMPTY_USER_FORM = {
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  job_role: '',
  role: 'ANALYST',
  password: '',
  is_active: true,
};

/**
 * Defangs ONLY affected or malicious assets, hostnames, domains, files, IPs, and URLs:
 *   https:// -> hxxps[:]//
 *   http://  -> hxxp[:]//
 *   192.168.1.1 -> 192.168[.]1.1
 *   domain.com  -> domain[.]com
 *   payload.exe -> payload[.]exe
 */
export function defangText(text) {
  if (!text) return '';
  let res = String(text);
  res = res.replace(/\bhttps:\/\//gi, 'hxxps[:]//');
  res = res.replace(/\bhttp:\/\//gi, 'hxxp[:]//');
  res = res.replace(/\bftp:\/\//gi, 'fxp[:]//');

  res = res.replace(
    /\b((?:25[0-5]|2[0-4]\d|1?\d?\d))\.(?:(25[0-5]|2[0-4]\d|1?\d?\d))\.(?:(25[0-5]|2[0-4]\d|1?\d?\d))\.(?:(25[0-5]|2[0-4]\d|1?\d?\d))\b/g,
    '$1.$2[.]$3.$4',
  );

  res = res.replace(
    /\b([a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*)\.([a-zA-Z0-9]{2,10})\b/g,
    (match, prefix, ext) => {
      if (/^\d+$/.test(prefix.replace(/\./g, '')) && /^\d+$/.test(ext)) {
        return match;
      }
      return `${prefix}[.]${ext}`;
    },
  );
  return res;
}

/**
 * Splits comma-, semicolon-, or newline-separated strings into unique items.
 */
function parseItems(rawText, additionalItems = [], shouldDefang = true) {
  const combined = [
    ...(rawText ? String(rawText).split(/[\r\n,;]+/) : []),
    ...additionalItems,
  ];
  const seen = new Set();
  const result = [];
  for (const part of combined) {
    const cleaned = String(part || '')
      .trim()
      .replace(/^[-*•\s]+/, '')
      .trim();
    if (!cleaned) continue;
    const formatted = shouldDefang ? defangText(cleaned) : cleaned;
    const lower = formatted.toLowerCase();
    if (!seen.has(lower)) {
      seen.add(lower);
      result.push(formatted);
    }
  }
  return result;
}

function toLocalDatetimeInput(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}

function fromDatetimeInputToIso(val) {
  if (!val) return null;
  if (val.endsWith('Z')) return val;
  return `${val}Z`;
}

function formatUtcTimestamp(isoString) {
  if (!isoString) return 'N/A';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
}

export default function App() {
  // Authentication & Navigation State
  const [authChecking, setAuthChecking] = useState(true);
  const [needsInitialSetup, setNeedsInitialSetup] = useState(false);
  const [authUser, setAuthUser] = useState(null);
  const [authError, setAuthError] = useState('');
  const [authSubmitting, setAuthSubmitting] = useState(false);

  // Login & Initial Setup forms
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [setupForm, setSetupForm] = useState({
    username: '',
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
  });

  // Main section switcher ('home' | 'investigations' | 'users') — defaults to top-level Homepage
  const [mainView, setMainView] = useState('home');

  // Investigation Data State
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [activeProject, setActiveProject] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'timeline' | 'reports'
  const [analystDirectory, setAnalystDirectory] = useState([]);
  const [demoScenarios, setDemoScenarios] = useState(DEFAULT_DEMO_SCENARIOS);

  // Sidebar Archived/Closed & Locked filters (both hidden by default)
  const [showArchivedSidebar, setShowArchivedSidebar] = useState(false);
  const [showLockedSidebar, setShowLockedSidebar] = useState(false);

  // Navbar dropdown states & outside-click refs
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showDemoDropdown, setShowDemoDropdown] = useState(false);
  const userDropdownRef = useRef(null);
  const demoDropdownRef = useRef(null);

  // Header status picker, Archive warning, & Project delete confirmation modal state
  const [showHeaderStatusPicker, setShowHeaderStatusPicker] = useState(false);
  const [showArchiveWarningModal, setShowArchiveWarningModal] = useState(false);
  const [pendingArchiveAction, setPendingArchiveAction] = useState(null);
  const [showDeleteProjectModal, setShowDeleteProjectModal] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Project create/edit modal state
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [editingProject, setEditingProject] = useState(false);
  const [projectForm, setProjectForm] = useState(EMPTY_PROJECT_FORM);

  // Evidence create/edit modal state
  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [editingEvidenceId, setEditingEvidenceId] = useState(null);
  const [evidenceForm, setEvidenceForm] = useState(EMPTY_EVIDENCE_FORM);
  const [screenshotFiles, setScreenshotFiles] = useState([]);
  const [screenshotCaption, setScreenshotCaption] = useState('');

  // External research form state
  const [researchLink, setResearchLink] = useState('');
  const [researchSummary, setResearchSummary] = useState('');

  // Evidence item detail popup & Screenshot Lightbox Modal
  const [detailEvidenceId, setDetailEvidenceId] = useState(null);
  const [previewScreenshot, setPreviewScreenshot] = useState(null);

  // Timeline filters
  const [filterKeyOnly, setFilterKeyOnly] = useState(false);
  const [filterType, setFilterType] = useState('ALL');
  const [searchFilter, setSearchFilter] = useState('');

  // User Management State (Admin / Super Admin)
  const [managedUsers, setManagedUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUserObj, setEditingUserObj] = useState(null);
  const [userForm, setUserForm] = useState(EMPTY_USER_FORM);

  // Password Reset Modal (Admin / Super Admin resetting lesser/other user)
  const [resetTargetUser, setResetTargetUser] = useState(null);
  const [resetNewPassword, setResetNewPassword] = useState('');

  // Delete User Confirmation Modal
  const [deleteTargetUser, setDeleteTargetUser] = useState(null);

  // Self Account / Profile / Password / API Token Modal
  const [showAccountModal, setShowAccountModal] = useState(false);

  // Derived permissions & lock state
  const perms = authUser?.permissions || {};
  const canEditRole = Boolean(perms.can_edit);
  const canLockProjects = Boolean(perms.can_lock_projects);
  const canDeleteProjects = Boolean(perms.can_delete_projects);
  const canManageUsers = Boolean(perms.can_manage_users);
  const canManageAdmins = Boolean(perms.can_manage_admins);
  const canAccessDbAdmin = Boolean(perms.can_access_db_admin);
  const canSeedDemo = Boolean(perms.can_seed_demo);

  const isProjectLocked = Boolean(activeProject?.is_locked);
  const canModifyActiveProject = canEditRole && !isProjectLocked;
  const currentAnalystName = authUser?.display_name || authUser?.username || '';

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (userDropdownRef.current && !userDropdownRef.current.contains(e.target)) {
        setShowUserDropdown(false);
      }
      if (demoDropdownRef.current && !demoDropdownRef.current.contains(e.target)) {
        setShowDemoDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const notifySuccess = useEventCallback((msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 3500);
  });

  const handleApiError = useEventCallback((err, prefix) => {
    if (err && err.status === 401) {
      setAuthUser(null);
      setAuthError('Your session has expired. Please sign in again.');
      return;
    }
    setErrorMsg(`${prefix}: ${err.message}`);
  });

  const loadAnalystDirectory = useEventCallback(async () => {
    try {
      const list = await api.listAnalysts();
      setAnalystDirectory(list || []);
    } catch {
      // Non-critical autocomplete helper
    }
  });

  const loadDemoScenarios = useEventCallback(async () => {
    if (!canSeedDemo) return;
    try {
      const list = await api.getDemoScenarios();
      if (Array.isArray(list) && list.length > 0) {
        setDemoScenarios(list);
      }
    } catch {
      // Fall back to built-in catalog metadata
    }
  });

  const loadProjects = useEventCallback(async (selectId = null, clearSelection = false) => {
    try {
      setLoading(true);
      const list = await api.listProjects();
      setProjects(list);
      const openUnlocked = list.filter((p) => p.status !== 'ARCHIVED' && !p.is_locked);
      const nonArchived = list.filter((p) => p.status !== 'ARCHIVED');
      const defaultFirst = openUnlocked[0] || nonArchived[0] || list[0];
      const candidateId = clearSelection
        ? selectId || (defaultFirst && defaultFirst.id)
        : selectId || selectedProjectId || (defaultFirst && defaultFirst.id);

      const existsInList = candidateId && list.some((p) => p.id === candidateId);
      const finalTargetId = existsInList ? candidateId : defaultFirst && defaultFirst.id;

      if (finalTargetId) {
        const detail = await api.getProject(finalTargetId);
        setSelectedProjectId(detail.id);
        setActiveProject(detail);
      } else {
        setSelectedProjectId(null);
        setActiveProject(null);
      }
    } catch (err) {
      handleApiError(err, 'Failed to load investigations');
    } finally {
      setLoading(false);
    }
  });

  const loadManagedUsers = useEventCallback(async () => {
    if (!canManageUsers) return;
    try {
      setUsersLoading(true);
      const list = await api.listUsers();
      setManagedUsers(list);
    } catch (err) {
      handleApiError(err, 'Failed to load user accounts');
    } finally {
      setUsersLoading(false);
    }
  });

  const initializeSession = useEventCallback(async () => {
    try {
      setAuthChecking(true);
      const statusData = await api.getAuthStatus();
      setNeedsInitialSetup(Boolean(statusData.needs_initial_setup));
      if (statusData.authenticated && statusData.user) {
        setAuthUser(statusData.user);
      } else {
        setAuthUser(null);
      }
    } catch (err) {
      setAuthError(`Unable to reach backend authentication service: ${err.message}`);
    } finally {
      setAuthChecking(false);
    }
  });

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  const authUserId = authUser?.id || null;

  useEffect(() => {
    if (authUserId) {
      loadProjects(null, true);
      loadAnalystDirectory();
      loadDemoScenarios();
    } else {
      setProjects([]);
      setSelectedProjectId(null);
      setActiveProject(null);
      setManagedUsers([]);
      setMainView('home');
    }
  }, [authUserId, loadProjects, loadAnalystDirectory, loadDemoScenarios]);

  useEffect(() => {
    if (authUser && mainView === 'users' && canManageUsers) {
      loadManagedUsers();
    }
  }, [authUser, mainView, canManageUsers, loadManagedUsers]);

  // --- Auth Handlers ---
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    setAuthSubmitting(true);
    try {
      const res = await api.login(loginUsername.trim(), loginPassword);
      setLoginPassword('');
      setMainView('home');
      setAuthUser(res.user);
      setNeedsInitialSetup(false);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleInitialSetupSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    if (setupForm.password !== setupForm.confirm_password) {
      setAuthError('Passwords do not match.');
      return;
    }
    setAuthSubmitting(true);
    try {
      const res = await api.initialSetup({
        username: setupForm.username.trim(),
        first_name: setupForm.first_name.trim(),
        last_name: setupForm.last_name.trim(),
        email: setupForm.email.trim(),
        password: setupForm.password,
      });
      setSetupForm({
        username: '',
        first_name: '',
        last_name: '',
        email: '',
        password: '',
        confirm_password: '',
      });
      setNeedsInitialSetup(false);
      setMainView('home');
      setAuthUser(res.user);
      notifySuccess('Initial Super Admin account created.');
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setShowUserDropdown(false);
    try {
      await api.logout();
    } catch {
      // Clear local session regardless
    }
    setAuthUser(null);
    setErrorMsg('');
    setSuccessMsg('');
    const statusData = await api.getAuthStatus().catch(() => null);
    if (statusData) {
      setNeedsInitialSetup(Boolean(statusData.needs_initial_setup));
    }
  };

  const openAccountSettings = () => {
    setShowUserDropdown(false);
    setShowAccountModal(true);
  };

  const handleProfileUpdated = async (updatedUser) => {
    setAuthUser(updatedUser);
    await loadAnalystDirectory();
  };

  // --- User Management Handlers ---
  const openCreateUserModal = () => {
    setEditingUserObj(null);
    setUserForm({
      ...EMPTY_USER_FORM,
      role: 'ANALYST',
    });
    setShowUserModal(true);
  };

  const openEditUserModal = (target) => {
    setEditingUserObj(target);
    setUserForm({
      username: target.username || '',
      first_name: target.first_name || '',
      last_name: target.last_name || '',
      email: target.email || '',
      job_role: target.job_role || '',
      role: target.role || 'ANALYST',
      password: '',
      is_active: Boolean(target.is_active),
    });
    setShowUserModal(true);
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    try {
      if (editingUserObj) {
        const payload = {
          first_name: userForm.first_name.trim(),
          last_name: userForm.last_name.trim(),
          email: userForm.email.trim(),
          job_role: userForm.job_role.trim(),
          role: userForm.role,
          is_active: userForm.is_active,
        };
        await api.updateUser(editingUserObj.id, payload);
        notifySuccess(`Updated account '${editingUserObj.username}'.`);
      } else {
        const payload = {
          username: userForm.username.trim(),
          first_name: userForm.first_name.trim(),
          last_name: userForm.last_name.trim(),
          email: userForm.email.trim(),
          job_role: userForm.job_role.trim(),
          role: userForm.role,
          password: userForm.password,
          is_active: userForm.is_active,
        };
        const created = await api.createUser(payload);
        notifySuccess(`Created ${ROLE_LABELS[created.role] || created.role} user '${created.username}'.`);
      }
      setShowUserModal(false);
      await loadManagedUsers();
      await loadAnalystDirectory();
    } catch (err) {
      handleApiError(err, 'Failed to save user');
    }
  };

  const handleConfirmPasswordReset = async (e) => {
    e.preventDefault();
    if (!resetTargetUser) return;
    try {
      await api.resetUserPassword(resetTargetUser.id, resetNewPassword);
      notifySuccess(`Password reset completed for '${resetTargetUser.username}'.`);
      setResetTargetUser(null);
      setResetNewPassword('');
    } catch (err) {
      handleApiError(err, 'Password reset failed');
    }
  };

  const handleConfirmDeleteUser = async () => {
    if (!deleteTargetUser) return;
    try {
      await api.deleteUser(deleteTargetUser.id);
      notifySuccess(`Deleted user '${deleteTargetUser.username}'.`);
      setDeleteTargetUser(null);
      await loadManagedUsers();
      await loadAnalystDirectory();
    } catch (err) {
      handleApiError(err, 'Failed to delete user');
    }
  };

  // --- Investigation Handlers ---
  const handleSelectProject = useEventCallback(async (id) => {
    try {
      setLoading(true);
      setShowHeaderStatusPicker(false);
      if (selectedProjectId !== id) {
        setDetailEvidenceId(null);
      }
      const detail = await api.getProject(id);
      setSelectedProjectId(detail.id);
      setActiveProject(detail);
      const list = await api.listProjects().catch(() => null);
      if (list) setProjects(list);
    } catch (err) {
      handleApiError(err, `Could not load investigation #${id}`);
    } finally {
      setLoading(false);
    }
  });

  const handleOpenInvestigationFromHome = useEventCallback(async (id) => {
    setMainView('investigations');
    setActiveTab('overview');
    await handleSelectProject(id);
  });

  const handleSeedDemo = useEventCallback(async (scenarioKey = 'expanse') => {
    if (!canSeedDemo) return;
    setShowDemoDropdown(false);
    try {
      setLoading(true);
      const result = await api.seedDemoProject(scenarioKey);
      const primaryId = result?.primary?.id || result?.id;
      await loadProjects(primaryId);
      if (scenarioKey === 'all') {
        notifySuccess(`Loaded all ${result?.count || 4} themed sample incidents.`);
      } else {
        notifySuccess(`Sample incident loaded: "${result?.title || scenarioKey}".`);
        setMainView('investigations');
      }
    } catch (err) {
      handleApiError(err, 'Failed to load sample investigation');
    } finally {
      setLoading(false);
    }
  });

  const handleToggleProjectLock = async () => {
    if (!activeProject || !canLockProjects) return;
    try {
      const updated = activeProject.is_locked
        ? await api.unlockProject(activeProject.id)
        : await api.lockProject(activeProject.id);
      setActiveProject(updated);
      await loadProjects(updated.id);
      notifySuccess(
        updated.is_locked
          ? 'Investigation locked (read-only). Toggle "Show Locked" in the sidebar to list locked items.'
          : 'Investigation unlocked (editing restored).',
      );
    } catch (err) {
      handleApiError(err, 'Failed to change investigation lock state');
    }
  };

  const handleConfirmDeleteProject = async () => {
    if (!activeProject || !canDeleteProjects) return;
    try {
      const deletedTitle = activeProject.title || `#${activeProject.id}`;
      await api.deleteProject(activeProject.id);
      setShowDeleteProjectModal(false);
      await loadProjects(null, true);
      notifySuccess(`Deleted investigation "${deletedTitle}".`);
    } catch (err) {
      setShowDeleteProjectModal(false);
      handleApiError(err, 'Failed to delete investigation');
    }
  };

  const applyStatusUpdate = async (newStatus) => {
    if (!activeProject) return;
    try {
      const updated = await api.updateProject(activeProject.id, { status: newStatus });
      setActiveProject(updated);
      await loadProjects(updated.id);
      setShowHeaderStatusPicker(false);
      notifySuccess(`Investigation status updated to ${STATUS_LABELS[newStatus] || newStatus}.`);
    } catch (err) {
      handleApiError(err, 'Failed to update status');
    }
  };

  const handleHeaderStatusSelect = (newStatus) => {
    setShowHeaderStatusPicker(false);
    if (!activeProject || newStatus === activeProject.status) return;
    if (newStatus === 'ARCHIVED') {
      setPendingArchiveAction(() => () => applyStatusUpdate('ARCHIVED'));
      setShowArchiveWarningModal(true);
    } else {
      applyStatusUpdate(newStatus);
    }
  };

  const openNewProjectModal = () => {
    setEditingProject(false);
    setProjectForm({
      ...EMPTY_PROJECT_FORM,
      lead_analyst: currentAnalystName,
    });
    setShowProjectModal(true);
  };

  const openEditProjectModal = () => {
    if (!activeProject) return;
    setEditingProject(true);
    setProjectForm({
      title: activeProject.title || '',
      customer_name: activeProject.customer_name || '',
      customer_id: activeProject.customer_id || '',
      ticket_id: activeProject.ticket_id || '',
      ticket_link: activeProject.ticket_link || '',
      summary: activeProject.summary || '',
      action_plan: activeProject.action_plan || '',
      key_customer_contacts: activeProject.key_customer_contacts || '',
      key_assets_affected: activeProject.key_assets_affected || '',
      key_users_affected: activeProject.key_users_affected || '',
      key_malicious_indicators: activeProject.key_malicious_indicators || '',
      external_research_link: '',
      external_research_summary: '',
      status: activeProject.status || 'INVESTIGATING',
      lead_analyst: activeProject.lead_analyst || currentAnalystName,
    });
    setShowProjectModal(true);
  };

  const executeSaveProject = async () => {
    try {
      if (editingProject && activeProject) {
        const updated = await api.updateProject(activeProject.id, projectForm);
        setActiveProject(updated);
        await loadProjects(updated.id);
        notifySuccess('Investigation overview updated.');
      } else {
        const created = await api.createProject(projectForm);
        await loadProjects(created.id);
        setMainView('investigations');
        notifySuccess(`Created investigation "${created.title || '#' + created.id}".`);
      }
      setShowProjectModal(false);
    } catch (err) {
      handleApiError(err, 'Failed to save investigation');
    }
  };

  const handleSaveProject = async (e) => {
    e.preventDefault();
    if (
      projectForm.status === 'ARCHIVED' &&
      (!editingProject || (activeProject && activeProject.status !== 'ARCHIVED'))
    ) {
      setPendingArchiveAction(() => () => executeSaveProject());
      setShowArchiveWarningModal(true);
      return;
    }
    await executeSaveProject();
  };

  const confirmArchiveAction = async () => {
    setShowArchiveWarningModal(false);
    if (pendingArchiveAction) {
      await pendingArchiveAction();
      setPendingArchiveAction(null);
    }
  };

  const openNewEvidenceModal = (defaultType = 'ATOMIC') => {
    setEditingEvidenceId(null);
    const nowIso = toLocalDatetimeInput(new Date().toISOString());
    setEvidenceForm({
      ...EMPTY_EVIDENCE_FORM,
      evidence_type: defaultType,
      analyst_name: currentAnalystName,
      timestamp: nowIso,
    });
    setScreenshotFiles([]);
    setScreenshotCaption('');
    setShowEvidenceModal(true);
  };

  const openEditEvidenceModal = (item) => {
    setEditingEvidenceId(item.id);
    setEvidenceForm({
      evidence_type: item.evidence_type || 'ATOMIC',
      analyst_name: item.analyst_name || currentAnalystName,
      timestamp: toLocalDatetimeInput(item.timestamp),
      end_timestamp: toLocalDatetimeInput(item.end_timestamp),
      summary: item.summary || '',
      affected_asset: item.affected_asset || '',
      affected_user: item.affected_user || '',
      user_created_by_attacker: Boolean(item.user_created_by_attacker),
      malicious_hosts_ips: item.malicious_hosts_ips || '',
      commands_run: item.commands_run || '',
      mitre_tactic: item.mitre_tactic || '',
      mitre_technique: item.mitre_technique || '',
      related_log_link: item.related_log_link || '',
      search_result_link: item.search_result_link || '',
      search_query_link: item.search_query_link || '',
      notes: item.notes || '',
      is_key_evidence: Boolean(item.is_key_evidence),
    });
    setScreenshotFiles([]);
    setScreenshotCaption('');
    setShowEvidenceModal(true);
  };

  const handleSaveEvidence = async (e) => {
    e.preventDefault();
    if (!activeProject) return;
    try {
      const formData = new FormData();
      formData.append('project', activeProject.id);
      formData.append('evidence_type', evidenceForm.evidence_type);
      formData.append('analyst_name', evidenceForm.analyst_name || currentAnalystName);

      const startIso = fromDatetimeInputToIso(evidenceForm.timestamp);
      if (startIso) {
        formData.append('timestamp', startIso);
      }
      const endIso = fromDatetimeInputToIso(evidenceForm.end_timestamp);
      if (evidenceForm.evidence_type === 'SEARCH' && endIso) {
        formData.append('end_timestamp', endIso);
      }

      formData.append('summary', evidenceForm.summary);
      formData.append('affected_asset', evidenceForm.affected_asset);
      formData.append('affected_user', evidenceForm.affected_user);
      formData.append(
        'user_created_by_attacker',
        evidenceForm.user_created_by_attacker ? 'true' : 'false',
      );
      formData.append('malicious_hosts_ips', evidenceForm.malicious_hosts_ips);
      formData.append('commands_run', evidenceForm.commands_run);
      formData.append('mitre_tactic', evidenceForm.mitre_tactic);
      formData.append('mitre_technique', evidenceForm.mitre_technique);
      formData.append('related_log_link', evidenceForm.related_log_link);
      formData.append('search_result_link', evidenceForm.search_result_link);
      formData.append('search_query_link', evidenceForm.search_query_link);
      formData.append('notes', evidenceForm.notes);
      formData.append('is_key_evidence', evidenceForm.is_key_evidence ? 'true' : 'false');

      for (const file of screenshotFiles) {
        formData.append('screenshots_upload', file);
        formData.append('screenshot_captions', screenshotCaption || file.name);
      }

      if (editingEvidenceId) {
        await api.updateEvidence(editingEvidenceId, formData);
        notifySuccess('Evidence item updated.');
      } else {
        await api.createEvidence(formData);
        notifySuccess('Evidence item added to timeline.');
      }
      setShowEvidenceModal(false);
      await handleSelectProject(activeProject.id);
    } catch (err) {
      handleApiError(err, 'Failed to save evidence');
    }
  };

  const handleToggleKeyEvidence = async (itemId) => {
    if (!activeProject || !canModifyActiveProject) return;
    try {
      await api.toggleKeyEvidence(itemId);
      await handleSelectProject(activeProject.id);
    } catch (err) {
      handleApiError(err, 'Could not toggle key evidence flag');
    }
  };

  const handleDeleteEvidence = async (itemId) => {
    if (!activeProject || !canModifyActiveProject) return;
    try {
      await api.deleteEvidence(itemId);
      await handleSelectProject(activeProject.id);
      notifySuccess('Evidence item deleted.');
    } catch (err) {
      handleApiError(err, 'Failed to delete evidence');
    }
  };

  const handleDeleteScreenshot = async (screenshotId) => {
    if (!activeProject || !canModifyActiveProject) return;
    try {
      await api.deleteScreenshot(screenshotId);
      if (previewScreenshot && previewScreenshot.id === screenshotId) {
        setPreviewScreenshot(null);
      }
      await handleSelectProject(activeProject.id);
      notifySuccess('Screenshot deleted from event.');
    } catch (err) {
      handleApiError(err, 'Failed to delete screenshot');
    }
  };

  const handleAddExternalResearch = async (e) => {
    e.preventDefault();
    if (!activeProject || !canModifyActiveProject) return;
    if (!researchLink.trim() && !researchSummary.trim()) return;
    try {
      await api.addExternalResearch({
        project: activeProject.id,
        link: researchLink.trim(),
        summary: researchSummary.trim(),
        analyst_name: currentAnalystName,
      });
      setResearchLink('');
      setResearchSummary('');
      await handleSelectProject(activeProject.id);
      notifySuccess('External research added.');
    } catch (err) {
      handleApiError(err, 'Could not add external research');
    }
  };

  const handleDeleteExternalResearch = async (id) => {
    if (!activeProject || !canModifyActiveProject) return;
    try {
      await api.deleteExternalResearch(id);
      await handleSelectProject(activeProject.id);
      notifySuccess('External research item removed.');
    } catch (err) {
      handleApiError(err, 'Failed to delete research entry');
    }
  };

  const handleClearLegacyInlineResearch = async () => {
    if (!activeProject || !canModifyActiveProject) return;
    try {
      await api.updateProject(activeProject.id, {
        external_research_link: '',
        external_research_summary: '',
      });
      await handleSelectProject(activeProject.id);
      notifySuccess('External research item removed.');
    } catch (err) {
      handleApiError(err, 'Failed to remove research item');
    }
  };

  // --- Initial Loading Screen ---
  if (authChecking) {
    return (
      <div className="auth-wrapper">
        <div className="text-center">
          <Spinner animation="border" variant="info" className="mb-3" />
          <div className="text-secondary small">Checking authentication status...</div>
        </div>
      </div>
    );
  }

  // --- First-Run Initial Super Admin Setup Screen ---
  if (!authUser && needsInitialSetup) {
    return (
      <div className="auth-wrapper">
        <Card className="soc-card auth-card shadow-lg">
          <Card.Header className="soc-card-header py-3 d-flex align-items-center gap-2">
            <Shield size={18} className="text-lb-cyan" />
            <span>Initial Super Admin Setup</span>
          </Card.Header>
          <Card.Body className="p-4">
            <p className="text-secondary small mb-3">
              No user accounts exist in this database yet. Create the initial{' '}
              <strong className="text-white">Super Admin</strong> account to get started.
            </p>
            {authError && (
              <Alert variant="danger" transition={false} className="py-2 small">
                {authError}
              </Alert>
            )}
            <Form onSubmit={handleInitialSetupSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="small">Username</Form.Label>
                <Form.Control
                  type="text"
                  required
                  autoFocus
                  value={setupForm.username}
                  onChange={(e) => setSetupForm({ ...setupForm, username: e.target.value })}
                />
              </Form.Group>
              <Row className="g-2 mb-3">
                <Col sm={6}>
                  <Form.Group>
                    <Form.Label className="small">First Name</Form.Label>
                    <Form.Control
                      type="text"
                      value={setupForm.first_name}
                      onChange={(e) => setSetupForm({ ...setupForm, first_name: e.target.value })}
                    />
                  </Form.Group>
                </Col>
                <Col sm={6}>
                  <Form.Group>
                    <Form.Label className="small">Last Name</Form.Label>
                    <Form.Control
                      type="text"
                      value={setupForm.last_name}
                      onChange={(e) => setSetupForm({ ...setupForm, last_name: e.target.value })}
                    />
                  </Form.Group>
                </Col>
              </Row>
              <Form.Group className="mb-3">
                <Form.Label className="small">Email (Optional)</Form.Label>
                <Form.Control
                  type="email"
                  value={setupForm.email}
                  onChange={(e) => setSetupForm({ ...setupForm, email: e.target.value })}
                />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label className="small">Password</Form.Label>
                <Form.Control
                  type="password"
                  required
                  value={setupForm.password}
                  onChange={(e) => setSetupForm({ ...setupForm, password: e.target.value })}
                />
              </Form.Group>
              <Form.Group className="mb-4">
                <Form.Label className="small">Confirm Password</Form.Label>
                <Form.Control
                  type="password"
                  required
                  value={setupForm.confirm_password}
                  onChange={(e) =>
                    setSetupForm({ ...setupForm, confirm_password: e.target.value })
                  }
                />
              </Form.Group>
              <Button
                type="submit"
                className="btn-lb-primary w-100"
                disabled={authSubmitting}
              >
                {authSubmitting ? 'Creating Super Admin...' : 'Create Super Admin & Sign In'}
              </Button>
            </Form>
          </Card.Body>
        </Card>
      </div>
    );
  }

  // --- Sign In Screen ---
  if (!authUser) {
    return (
      <div className="auth-wrapper">
        <Card className="soc-card auth-card shadow-lg">
          <Card.Header className="soc-card-header py-3 d-flex align-items-center gap-2">
            <Shield size={18} className="text-lb-cyan" />
            <span>SOC Investigations — Sign In</span>
          </Card.Header>
          <Card.Body className="p-4">
            <p className="text-secondary small mb-3">
              Sign in with your SOC account (Super Admin, Admin, Analyst, or Executive).
            </p>
            {authError && (
              <Alert variant="danger" transition={false} className="py-2 small">
                {authError}
              </Alert>
            )}
            <Form onSubmit={handleLoginSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="small">Username</Form.Label>
                <Form.Control
                  type="text"
                  required
                  autoFocus
                  autoComplete="username"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                />
              </Form.Group>
              <Form.Group className="mb-4">
                <Form.Label className="small">Password</Form.Label>
                <Form.Control
                  type="password"
                  required
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                />
              </Form.Group>
              <Button
                type="submit"
                className="btn-lb-primary w-100"
                disabled={authSubmitting}
              >
                {authSubmitting ? 'Signing in...' : 'Sign In'}
              </Button>
            </Form>
          </Card.Body>
        </Card>
      </div>
    );
  }

  // Sidebar projects filtering:
  // Locked projects are hidden by default unless showLockedSidebar is enabled.
  // Archived (unlocked) projects are hidden by default unless showArchivedSidebar is enabled.
  const lockedCount = projects.filter((p) => Boolean(p.is_locked)).length;
  const archivedCount = projects.filter((p) => !p.is_locked && p.status === 'ARCHIVED').length;
  const visibleSidebarProjects = projects.filter((p) => {
    if (p.is_locked) {
      return showLockedSidebar;
    }
    if (p.status === 'ARCHIVED') {
      return showArchivedSidebar;
    }
    return true;
  });

  const userInitials = (() => {
    const src = currentAnalystName || '?';
    const parts = src.trim().split(/\s+/);
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }
    return src.slice(0, 2).toUpperCase();
  })();

  const timelineItems = activeProject?.timeline_evidence || [];

  // Aggregate lists for Overview & Bottom Summary Tables
  // Affected assets & malicious indicators ARE defanged; users are NOT defanged.
  const assetList = activeProject
    ? parseItems(
        activeProject.key_assets_affected,
        timelineItems.map((e) => e.affected_asset).filter(Boolean),
        true,
      )
    : [];

  const userList = activeProject
    ? parseItems(
        activeProject.key_users_affected,
        timelineItems
          .filter((e) => e.affected_user)
          .map((e) =>
            e.user_created_by_attacker
              ? `${e.affected_user} (Created by Attacker)`
              : e.affected_user,
          ),
        false,
      )
    : [];

  const indicatorList = activeProject
    ? parseItems(
        activeProject.key_malicious_indicators,
        timelineItems
          .flatMap((e) => (e.malicious_hosts_ips ? e.malicious_hosts_ips.split(/[\r\n,;]+/) : []))
          .filter(Boolean),
        true,
      )
    : [];

  const filteredTimeline = timelineItems.filter((item) => {
    if (filterKeyOnly && !item.is_key_evidence) return false;
    if (filterType !== 'ALL' && item.evidence_type !== filterType) return false;
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      const haystack = [
        item.summary,
        item.affected_asset,
        item.affected_user,
        item.malicious_hosts_ips,
        item.commands_run,
        item.mitre_tactic,
        item.mitre_technique,
        item.analyst_name,
        item.notes,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });

  const keyEvidenceItems = timelineItems.filter((i) => i.is_key_evidence);
  const currentlyEditingItem = editingEvidenceId
    ? timelineItems.find((i) => i.id === editingEvidenceId)
    : null;
  const detailEvidenceItem = detailEvidenceId
    ? timelineItems.find((i) => i.id === detailEvidenceId) || null
    : null;

  const analystSuggestions = Array.from(
    new Set(
      [
        currentAnalystName,
        ...analystDirectory.map((u) => u.display_name),
        'Chrisjen Avasarala',
        'James Holden',
      ].filter(Boolean),
    ),
  );

  // Roles assignable by the logged-in user inside User Management
  const assignableRoles = canManageAdmins
    ? [
        ['SUPER_ADMIN', 'Super Admin (Full System & Admin Management)'],
        ['ADMIN', 'Admin (User & Investigation Administration)'],
        ['ANALYST', 'Analyst (Create & Modify Investigations)'],
        ['EXECUTIVE', 'Executive (Read-Only & Report Export)'],
      ]
    : [
        ['ANALYST', 'Analyst (Create & Modify Investigations)'],
        ['EXECUTIVE', 'Executive (Read-Only & Report Export)'],
      ];

  const topMenuRoleText = authUser.job_role || ROLE_LABELS[authUser.role] || authUser.role;

  return (
    <div className="min-vh-100 d-flex flex-column">
      {/* Datalist for Analyst suggestions */}
      <datalist id="soc-analysts-list">
        {analystSuggestions.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>

      {/* Top Navigation Bar */}
      <Navbar className="soc-navbar py-2 px-3" variant="dark" expand="lg">
        <Container fluid>
          <div className="d-flex align-items-center gap-3 flex-wrap">
            <Navbar.Brand
              role="button"
              onClick={() => setMainView('home')}
              className="fw-semibold text-white me-1"
              style={{ cursor: 'pointer' }}
            >
              SOC Investigations
            </Navbar.Brand>

            <div className="d-flex align-items-center gap-1">
              <Button
                size="sm"
                className={mainView === 'home' ? 'btn-lb-primary' : ''}
                variant={mainView === 'home' ? undefined : 'outline-secondary'}
                onClick={() => setMainView('home')}
              >
                <Home size={14} className="me-1" />
                Home
              </Button>
              <Button
                size="sm"
                className={mainView === 'investigations' ? 'btn-lb-primary' : ''}
                variant={mainView === 'investigations' ? undefined : 'outline-secondary'}
                onClick={() => setMainView('investigations')}
              >
                <FolderOpen size={14} className="me-1" />
                Investigations
              </Button>
            </div>
          </div>

          <div className="d-flex align-items-center flex-wrap gap-2 ms-auto mt-2 mt-lg-0">
            {/* Super Admin Only: Load Sample Incident Dropdown (4 Themed Scenarios) */}
            {canSeedDemo && (
              <div className="position-relative" ref={demoDropdownRef}>
                <Button
                  className="btn-lb-cyan d-inline-flex align-items-center gap-1"
                  size="sm"
                  onClick={() => setShowDemoDropdown((prev) => !prev)}
                >
                  <Sparkles size={14} />
                  <span>Load Sample Incident</span>
                  <ChevronDown size={13} />
                </Button>

                {showDemoDropdown && (
                  <div className="soc-dropdown-panel shadow-lg p-2" style={{ minWidth: '340px' }}>
                    <div className="px-2 py-1 small text-secondary border-bottom border-secondary mb-1">
                      Super Admin Demo Scenarios
                    </div>
                    {demoScenarios.map((sc) => (
                      <button
                        key={sc.id}
                        type="button"
                        className="soc-dropdown-item flex-column align-items-start gap-0"
                        onClick={() => handleSeedDemo(sc.id)}
                      >
                        <span className="fw-semibold text-lb-cyan">{sc.label}</span>
                        {sc.customer_name && (
                          <span className="text-secondary" style={{ fontSize: '0.75rem' }}>
                            Customer: {sc.customer_name}
                          </span>
                        )}
                      </button>
                    ))}
                    <div className="border-top border-secondary mt-1 pt-1">
                      <button
                        type="button"
                        className="soc-dropdown-item text-lb-lime fw-semibold"
                        onClick={() => handleSeedDemo('all')}
                      >
                        <Sparkles size={14} />
                        <span>Load All 4 Sample Incidents</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {canEditRole && (
              <Button className="btn-lb-green" size="sm" onClick={openNewProjectModal}>
                <Plus size={15} className="me-1" />
                New Investigation
              </Button>
            )}

            {/* User Name Dropdown Menu (Preferred Username + Role only on top button) */}
            <div className="position-relative" ref={userDropdownRef}>
              <button
                type="button"
                onClick={() => setShowUserDropdown((prev) => !prev)}
                className="user-menu-trigger d-inline-flex align-items-center gap-2"
                title="Open account and user options"
              >
                {authUser.avatar_url ? (
                  <img
                    src={authUser.avatar_url}
                    alt={currentAnalystName}
                    className="user-avatar-circle"
                  />
                ) : (
                  <span className="user-avatar-circle">{userInitials}</span>
                )}
                <span className="small text-white fw-semibold">{currentAnalystName}</span>
                <Badge bg={ROLE_BADGE_BG[authUser.role] || 'secondary'} style={{ fontSize: '0.68rem' }}>
                  {topMenuRoleText}
                </Badge>
                <ChevronDown size={14} className="text-secondary" />
              </button>

              {showUserDropdown && (
                <div className="soc-dropdown-panel shadow-lg p-2">
                  <div className="px-2 py-2 border-bottom border-secondary mb-1">
                    <div className="fw-semibold text-white small">
                      {currentAnalystName}
                      {authUser.pronouns ? ` (${authUser.pronouns})` : ''}
                    </div>
                    <div className="text-lb-cyan" style={{ fontSize: '0.75rem' }}>
                      {authUser.job_role ? `${authUser.job_role} • ` : ''}
                      {ROLE_LABELS[authUser.role] || authUser.role}
                    </div>
                    <div className="mono-text text-secondary" style={{ fontSize: '0.75rem' }}>
                      @{authUser.username}
                      {authUser.email ? ` • ${authUser.email}` : ''}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="soc-dropdown-item"
                    onClick={openAccountSettings}
                  >
                    <Settings size={15} className="text-lb-cyan" />
                    <span>Account, Avatar &amp; Preferences</span>
                  </button>

                  {canManageUsers && (
                    <button
                      type="button"
                      className="soc-dropdown-item"
                      onClick={() => {
                        setShowUserDropdown(false);
                        setMainView('users');
                      }}
                    >
                      <Users size={15} className="text-lb-cyan" />
                      <span>User &amp; Role Management</span>
                    </button>
                  )}

                  {canAccessDbAdmin && (
                    <a
                      href="/admin/"
                      target="_blank"
                      rel="noreferrer"
                      className="soc-dropdown-item"
                      onClick={() => setShowUserDropdown(false)}
                    >
                      <Database size={15} className="text-lb-cyan" />
                      <span>Django Database Admin</span>
                      <ExternalLink size={12} className="ms-auto text-secondary" />
                    </a>
                  )}

                  <div className="border-top border-secondary mt-1 pt-1">
                    <button
                      type="button"
                      className="soc-dropdown-item text-danger"
                      onClick={handleLogout}
                    >
                      <LogOut size={15} />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Container>
      </Navbar>

      <Container fluid className="flex-grow-1 py-4 px-4">
        {errorMsg && (
          <Alert
            variant="danger"
            dismissible
            transition={false}
            onClose={() => setErrorMsg('')}
            className="mb-3"
          >
            {errorMsg}
          </Alert>
        )}
        {successMsg && (
          <Alert
            variant="info"
            dismissible
            transition={false}
            onClose={() => setSuccessMsg('')}
            className="mb-3 bg-dark text-light border-info"
          >
            {successMsg}
          </Alert>
        )}

        {/* ==================== TOP-LEVEL HOMEPAGE (DEFAULT VIEW) ==================== */}
        {mainView === 'home' ? (
          <HomeDashboard
            projects={projects}
            loading={loading}
            canEditRole={canEditRole}
            canSeedDemo={canSeedDemo}
            onOpenInvestigation={handleOpenInvestigationFromHome}
            onOpenNewProject={openNewProjectModal}
            onSeedDemoScenario={handleSeedDemo}
            demoScenarios={demoScenarios}
          />
        ) : mainView === 'users' && canManageUsers ? (
          /* ==================== USER MANAGEMENT VIEW (ADMIN & SUPER ADMIN) ==================== */
          <Card className="soc-card">
            <Card.Header className="soc-card-header py-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
              <div>
                <div className="fw-semibold text-white">User &amp; Role Administration</div>
                <div className="small text-secondary fw-normal mt-1">
                  {canManageAdmins
                    ? 'Super Admin access: create and manage Super Admin, Admin, Analyst, and Executive users.'
                    : 'Admin access: create and manage Analyst and Executive users, assign roles, and reset passwords for lesser users.'}
                </div>
              </div>
              <Button className="btn-lb-primary" size="sm" onClick={openCreateUserModal}>
                <UserPlus size={15} className="me-1" />
                Create User
              </Button>
            </Card.Header>
            <Card.Body className="p-0">
              {usersLoading ? (
                <div className="text-center py-5">
                  <Spinner animation="border" variant="info" size="sm" />
                </div>
              ) : (
                <Table responsive hover variant="dark" className="mb-0 align-middle">
                  <thead className="small text-secondary text-uppercase">
                    <tr>
                      <th>Username</th>
                      <th>Display Name &amp; Pronouns</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Last Login (UTC)</th>
                      <th className="text-end">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {managedUsers.map((u) => (
                      <tr key={u.id}>
                        <td className="mono-text fw-semibold text-white">
                          <div className="d-flex align-items-center gap-2">
                            {u.avatar_url ? (
                              <img src={u.avatar_url} alt={u.username} className="user-avatar-circle" />
                            ) : (
                              <span className="user-avatar-circle">
                                {(u.display_name || u.username || '?').slice(0, 2).toUpperCase()}
                              </span>
                            )}
                            <span>{u.username}</span>
                            {u.is_self && (
                              <Badge bg="secondary" style={{ fontSize: '0.68rem' }}>
                                You
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td>
                          <div>
                            <span>{u.display_name || '—'}</span>
                            {u.pronouns && (
                              <span className="text-secondary small ms-1">({u.pronouns})</span>
                            )}
                          </div>
                          {u.job_role && (
                            <div className="text-lb-cyan" style={{ fontSize: '0.74rem' }}>
                              {u.job_role}
                            </div>
                          )}
                        </td>
                        <td className="text-secondary small">{u.email || '—'}</td>
                        <td>
                          <Badge bg={ROLE_BADGE_BG[u.role] || 'secondary'}>
                            {u.role_display || ROLE_LABELS[u.role] || u.role}
                          </Badge>
                        </td>
                        <td>
                          {u.is_active ? (
                            <Badge bg="success">Active</Badge>
                          ) : (
                            <Badge bg="secondary">Disabled</Badge>
                          )}
                        </td>
                        <td className="mono-text small text-secondary">
                          {u.last_login ? formatUtcTimestamp(u.last_login) : 'Never'}
                        </td>
                        <td className="text-end">
                          {u.can_actor_modify ? (
                            <div className="d-flex justify-content-end gap-2">
                              <Button
                                variant="outline-light"
                                size="sm"
                                onClick={() => openEditUserModal(u)}
                              >
                                <Edit3 size={13} className="me-1" />
                                Edit / Role
                              </Button>
                              <Button
                                className="btn-lb-cyan"
                                size="sm"
                                onClick={() => {
                                  setResetTargetUser(u);
                                  setResetNewPassword('');
                                }}
                              >
                                <KeyRound size={13} className="me-1" />
                                Reset Password
                              </Button>
                              {!u.is_self && (
                                <Button
                                  variant="outline-danger"
                                  size="sm"
                                  onClick={() => setDeleteTargetUser(u)}
                                >
                                  <Trash2 size={13} />
                                </Button>
                              )}
                            </div>
                          ) : (
                            <span className="small text-secondary">Protected</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        ) : (
          /* ==================== INVESTIGATIONS WORKSPACE VIEW ==================== */
          <Row className="g-4">
            {/* Left Sidebar: Investigations List */}
            <Col lg={3} xl={2}>
              <Card className="soc-card">
                <Card.Header className="soc-card-header py-2">
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="small text-uppercase text-secondary">
                      Investigations ({visibleSidebarProjects.length})
                    </span>
                  </div>
                  <div className="mt-2 pt-1 border-top border-secondary d-flex flex-column gap-1">
                    <Form.Check
                      type="switch"
                      id="show-archived-switch"
                      label={`Show Archived (${archivedCount})`}
                      checked={showArchivedSidebar}
                      onChange={(e) => setShowArchivedSidebar(e.target.checked)}
                      className="small text-secondary"
                    />
                    <Form.Check
                      type="switch"
                      id="show-locked-switch"
                      label={`Show Locked (${lockedCount})`}
                      checked={showLockedSidebar}
                      onChange={(e) => setShowLockedSidebar(e.target.checked)}
                      className="small text-secondary"
                    />
                  </div>
                </Card.Header>
                <Card.Body className="p-2">
                  {loading && projects.length === 0 ? (
                    <div className="text-center py-4">
                      <Spinner animation="border" size="sm" variant="info" />
                    </div>
                  ) : visibleSidebarProjects.length === 0 ? (
                    <div className="text-center py-3 px-2 text-secondary small">
                      <p className="mb-2">
                        {projects.length > 0
                          ? 'No open unlocked investigations. Toggle "Show Archived" or "Show Locked" above.'
                          : 'No investigations created yet.'}
                      </p>
                      {canEditRole && (
                        <Button
                          className="btn-lb-green w-100"
                          size="sm"
                          onClick={openNewProjectModal}
                        >
                          <Plus size={14} className="me-1" />
                          New Investigation
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="d-flex flex-column gap-2">
                      {visibleSidebarProjects.map((p) => {
                        const isSelected = activeProject && activeProject.id === p.id;
                        return (
                          <div
                            key={p.id}
                            onClick={() => handleSelectProject(p.id)}
                            className={`p-2 rounded project-list-item ${
                              isSelected ? 'active-project' : ''
                            }`}
                          >
                            <div className="d-flex justify-content-between align-items-start gap-1">
                              <div className="fw-semibold small text-white text-truncate">
                                {p.title || `Investigation #${p.id}`}
                              </div>
                              {p.is_locked && (
                                <Lock
                                  size={13}
                                  className="text-warning flex-shrink-0 mt-1"
                                  title="Locked (Read-Only)"
                                />
                              )}
                            </div>
                            <div className="mt-1 mb-1 d-flex flex-wrap gap-1">
                              <Badge
                                bg={p.status === 'ARCHIVED' ? 'secondary' : 'dark'}
                                className="border border-secondary text-lb-cyan fw-normal"
                                style={{ fontSize: '0.68rem' }}
                              >
                                {STATUS_LABELS[p.status] || p.status}
                              </Badge>
                              {p.is_locked && (
                                <Badge
                                  bg="warning"
                                  text="dark"
                                  style={{ fontSize: '0.66rem' }}
                                >
                                  Locked
                                </Badge>
                              )}
                            </div>
                            <div className="text-secondary" style={{ fontSize: '0.75rem' }}>
                              <div>{p.customer_name || 'No Customer'}</div>
                              <div>
                                {p.ticket_id || 'No Ticket'} &bull; {p.evidence_count} events (
                                {p.key_evidence_count} key)
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>

            {/* Main Investigation Area */}
            <Col lg={9} xl={10}>
              {!activeProject ? (
                <Card className="soc-card text-center py-5">
                  <Card.Body>
                    <h5 className="text-white mb-2">
                      {canEditRole
                        ? 'Select or Create an Investigation'
                        : 'Select an Investigation'}
                    </h5>
                    <p className="text-secondary small mb-3">
                      {canEditRole
                        ? 'Create a new investigation or select one from the sidebar to begin recording evidence.'
                        : 'Select an investigation from the sidebar to review evidence and export reports.'}
                    </p>
                    <div className="d-flex justify-content-center gap-2">
                      {canEditRole && (
                        <Button className="btn-lb-green" onClick={openNewProjectModal}>
                          <Plus size={15} className="me-1" />
                          New Investigation
                        </Button>
                      )}
                      {canSeedDemo && (
                        <Button className="btn-lb-cyan" onClick={() => handleSeedDemo('expanse')}>
                          Load Sample Incident
                        </Button>
                      )}
                    </div>
                  </Card.Body>
                </Card>
              ) : (
                <>
                  {/* Investigation Header */}
                  <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                    <div>
                      <div className="d-flex align-items-center gap-2 mb-1">
                        <h4 className="mb-0 text-white fw-semibold">
                          {activeProject.title || `Investigation #${activeProject.id}`}
                        </h4>
                        {isProjectLocked && (
                          <Badge bg="warning" text="dark" className="d-inline-flex align-items-center gap-1">
                            <Lock size={12} />
                            Locked (Read-Only)
                          </Badge>
                        )}
                      </div>
                      <div className="text-secondary small d-flex flex-wrap align-items-center gap-3">
                        <span>Customer: {activeProject.customer_name || 'N/A'}</span>
                        <span>Customer ID: {activeProject.customer_id || 'N/A'}</span>
                        <span>
                          Ticket:{' '}
                          {activeProject.ticket_link ? (
                            <a
                              href={activeProject.ticket_link}
                              target="_blank"
                              rel="noreferrer"
                              className="text-lb-cyan text-decoration-none"
                            >
                              {activeProject.ticket_id || activeProject.ticket_link}{' '}
                              <ExternalLink size={12} />
                            </a>
                          ) : (
                            activeProject.ticket_id || 'N/A'
                          )}
                        </span>

                        {/* Status Picker (clickable only when user can modify unlocked project) */}
                        {canModifyActiveProject ? (
                          <div className="position-relative d-inline-block">
                            <button
                              type="button"
                              onClick={() => setShowHeaderStatusPicker((prev) => !prev)}
                              className="btn btn-sm btn-outline-light py-1 px-2 d-inline-flex align-items-center gap-1"
                              style={{ fontSize: '0.78rem' }}
                              title="Click to change investigation status"
                            >
                              <span>
                                Status:{' '}
                                <strong>
                                  {STATUS_LABELS[activeProject.status] || activeProject.status}
                                </strong>
                              </span>
                              <ChevronDown size={13} />
                            </button>

                            {showHeaderStatusPicker && (
                              <div
                                className="position-absolute start-0 mt-1 p-1 rounded soc-card shadow-lg"
                                style={{ zIndex: 1050, minWidth: '190px' }}
                              >
                                {Object.entries(STATUS_LABELS).map(([code, label]) => (
                                  <button
                                    key={code}
                                    type="button"
                                    onClick={() => handleHeaderStatusSelect(code)}
                                    className={`btn btn-sm w-100 text-start py-1 px-2 ${
                                      activeProject.status === code
                                        ? 'btn-lb-primary'
                                        : 'btn-dark bg-transparent border-0 text-light'
                                    }`}
                                  >
                                    {label}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span>
                            Status:{' '}
                            <strong className="text-light">
                              {STATUS_LABELS[activeProject.status] || activeProject.status}
                            </strong>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="d-flex flex-wrap gap-2 mt-2 mt-md-0">
                      {canModifyActiveProject && (
                        <>
                          <Button
                            className="btn-lb-primary"
                            size="sm"
                            onClick={() => openNewEvidenceModal('ATOMIC')}
                          >
                            <Plus size={14} className="me-1" />
                            Add Atomic Event
                          </Button>
                          <Button
                            className="btn-lb-cyan"
                            size="sm"
                            onClick={() => openNewEvidenceModal('SEARCH')}
                          >
                            <Plus size={14} className="me-1" />
                            Add Search Result
                          </Button>
                          <Button
                            variant="outline-light"
                            size="sm"
                            onClick={openEditProjectModal}
                          >
                            <Edit3 size={14} className="me-1" />
                            Edit Investigation
                          </Button>
                        </>
                      )}

                      {canLockProjects && (
                        <Button
                          variant={isProjectLocked ? 'warning' : 'outline-warning'}
                          size="sm"
                          onClick={handleToggleProjectLock}
                          title={
                            isProjectLocked
                              ? 'Unlock investigation to allow editing'
                              : 'Lock investigation to make it read-only'
                          }
                        >
                          {isProjectLocked ? (
                            <>
                              <Unlock size={14} className="me-1" />
                              Unlock Investigation
                            </>
                          ) : (
                            <>
                              <Lock size={14} className="me-1" />
                              Lock Investigation
                            </>
                          )}
                        </Button>
                      )}

                      {canDeleteProjects && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          disabled={isProjectLocked}
                          title={
                            isProjectLocked
                              ? 'Unlock this investigation before deleting it'
                              : 'Delete investigation permanently'
                          }
                          onClick={() => setShowDeleteProjectModal(true)}
                        >
                          <Trash2 size={14} className="me-1" />
                          Delete
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Read-Only Banner when Investigation is Locked */}
                  {isProjectLocked && (
                    <div className="locked-banner px-3 py-2 mb-3 small d-flex flex-wrap justify-content-between align-items-center gap-2">
                      <div className="d-flex align-items-center gap-2">
                        <Lock size={15} />
                        <span>
                          <strong>Investigation Locked (Read-Only):</strong> Modifications to overview,
                          evidence, research, and screenshots are disabled
                          {activeProject.locked_by_display
                            ? ` (locked by ${activeProject.locked_by_display}${
                                activeProject.locked_at
                                  ? ` on ${formatUtcTimestamp(activeProject.locked_at)}`
                                  : ''
                              })`
                            : ''}
                          . Reports remain available for export.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 3-Tab Navigation */}
                  <Nav
                    variant="tabs"
                    className="mb-3"
                    activeKey={activeTab}
                    onSelect={(k) => setActiveTab(k)}
                  >
                    <Nav.Item>
                      <Nav.Link eventKey="overview">Overview</Nav.Link>
                    </Nav.Item>
                    <Nav.Item>
                      <Nav.Link eventKey="timeline">Evidence Timeline</Nav.Link>
                    </Nav.Item>
                    <Nav.Item>
                      <Nav.Link eventKey="reports">Report Generation</Nav.Link>
                    </Nav.Item>
                  </Nav>

                  {/* TAB 1: INVESTIGATION OVERVIEW */}
                  {activeTab === 'overview' && (
                    <div className="d-flex flex-column gap-3">
                      <Card className="soc-card">
                        <Card.Header className="soc-card-header d-flex justify-content-between align-items-center">
                          <span>Investigation Overview</span>
                          {canModifyActiveProject && (
                            <Button
                              variant="outline-light"
                              size="sm"
                              onClick={openEditProjectModal}
                            >
                              Edit Overview
                            </Button>
                          )}
                        </Card.Header>
                        <Card.Body>
                          <Row className="mb-3 g-3">
                            <Col md={4}>
                              <div className="text-secondary small">Customer</div>
                              <div className="fw-semibold">
                                {activeProject.customer_name || 'N/A'}{' '}
                                {activeProject.customer_id ? `(${activeProject.customer_id})` : ''}
                              </div>
                            </Col>
                            <Col md={4}>
                              <div className="text-secondary small">Ticket Link</div>
                              <div>
                                {activeProject.ticket_link ? (
                                  <a
                                    href={activeProject.ticket_link}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-lb-cyan text-decoration-none"
                                  >
                                    {activeProject.ticket_id || activeProject.ticket_link}{' '}
                                    <ExternalLink size={12} />
                                  </a>
                                ) : (
                                  activeProject.ticket_id || 'N/A'
                                )}
                              </div>
                            </Col>
                            <Col md={4}>
                              <div className="text-secondary small">Archive Folder</div>
                              <div className="mono-text small">
                                artifacts/{activeProject.artifact_folder}/
                              </div>
                            </Col>
                          </Row>

                          <div className="mb-4">
                            <div className="text-secondary small mb-1">Summary of Investigation</div>
                            <div className="p-3 soc-subbox">
                              {activeProject.summary || 'No summary provided.'}
                            </div>
                          </div>

                          {/* Bulleted Lists for Affected Assets (defanged), Users, and Malicious Indicators (defanged) */}
                          <Row className="g-3">
                            <Col md={4}>
                              <div className="p-3 soc-subbox h-100">
                                <div className="fw-semibold mb-2 text-lb-cyan">
                                  Key Affected Assets (Defanged)
                                </div>
                                {assetList.length === 0 ? (
                                  <div className="text-secondary small">None recorded</div>
                                ) : (
                                  <ul className="bullet-list mono-text">
                                    {assetList.map((asset, i) => (
                                      <li key={i}>{asset}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            </Col>

                            <Col md={4}>
                              <div className="p-3 soc-subbox h-100">
                                <div className="fw-semibold mb-2 text-lb-cyan">
                                  Key Affected Users
                                </div>
                                {userList.length === 0 ? (
                                  <div className="text-secondary small">None recorded</div>
                                ) : (
                                  <ul className="bullet-list mono-text">
                                    {userList.map((u, i) => (
                                      <li key={i}>{u}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            </Col>

                            <Col md={4}>
                              <div className="p-3 soc-subbox h-100">
                                <div className="fw-semibold mb-2 text-lb-cyan">
                                  Key Malicious Indicators (Defanged)
                                </div>
                                {indicatorList.length === 0 ? (
                                  <div className="text-secondary small">None recorded</div>
                                ) : (
                                  <ul className="bullet-list mono-text">
                                    {indicatorList.map((ind, i) => (
                                      <li key={i}>{ind}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            </Col>
                          </Row>
                        </Card.Body>
                      </Card>

                      {/* Action Plan, Related Escalated Incidents & Key Customer Contacts */}
                      <ProjectOverviewExtras
                        activeProject={activeProject}
                        canModifyActiveProject={canModifyActiveProject}
                        currentAnalystName={currentAnalystName}
                        onProjectMutated={handleSelectProject}
                        onNotifySuccess={notifySuccess}
                        onApiError={handleApiError}
                      />

                      {/* External Research Links & Summaries */}
                      <Card className="soc-card">
                        <Card.Header className="soc-card-header">
                          External Research &amp; Threat Intelligence Links
                        </Card.Header>
                        <Card.Body>
                          <ul
                            className={`bullet-list ${canModifyActiveProject ? 'mb-3' : 'mb-0'}`}
                          >
                            {(activeProject.external_research_link ||
                              activeProject.external_research_summary) && (
                              <li className="mb-2">
                                <div className="d-flex justify-content-between align-items-start">
                                  <div>
                                    {activeProject.external_research_link && (
                                      <div>
                                        <a
                                          href={activeProject.external_research_link}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="text-lb-cyan mono-text text-decoration-none"
                                        >
                                          {activeProject.external_research_link}{' '}
                                          <ExternalLink size={12} />
                                        </a>
                                      </div>
                                    )}
                                    <div className="text-secondary small">
                                      {activeProject.external_research_summary}
                                    </div>
                                  </div>
                                  {canModifyActiveProject && (
                                    <Button
                                      variant="outline-secondary"
                                      size="sm"
                                      title="Remove external research item"
                                      onClick={handleClearLegacyInlineResearch}
                                    >
                                      <Trash2 size={13} />
                                    </Button>
                                  )}
                                </div>
                              </li>
                            )}

                            {(activeProject.external_research_items || []).map((r) => (
                              <li key={r.id} className="mb-2">
                                <div className="d-flex justify-content-between align-items-start">
                                  <div>
                                    {r.link && (
                                      <div>
                                        <a
                                          href={r.link}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="text-lb-cyan mono-text text-decoration-none"
                                        >
                                          {r.link} <ExternalLink size={12} />
                                        </a>
                                      </div>
                                    )}
                                    <div className="text-secondary small">{r.summary}</div>
                                    {r.analyst_name && (
                                      <div
                                        className="text-secondary"
                                        style={{ fontSize: '0.72rem' }}
                                      >
                                        Added by {r.analyst_name}
                                      </div>
                                    )}
                                  </div>
                                  {canModifyActiveProject && (
                                    <Button
                                      variant="outline-secondary"
                                      size="sm"
                                      title="Remove external research item"
                                      onClick={() => handleDeleteExternalResearch(r.id)}
                                    >
                                      <Trash2 size={13} />
                                    </Button>
                                  )}
                                </div>
                              </li>
                            ))}

                            {!activeProject.external_research_link &&
                              !activeProject.external_research_summary &&
                              (!activeProject.external_research_items ||
                                activeProject.external_research_items.length === 0) && (
                                <li className="text-secondary small">
                                  No external research recorded.
                                </li>
                              )}
                          </ul>

                          {canModifyActiveProject && (
                            <Form onSubmit={handleAddExternalResearch}>
                              <Row className="g-2">
                                <Col md={5}>
                                  <Form.Control
                                    size="sm"
                                    type="text"
                                    placeholder="External link (e.g. https://attack.mitre.org/...)"
                                    value={researchLink}
                                    onChange={(e) => setResearchLink(e.target.value)}
                                  />
                                </Col>
                                <Col md={5}>
                                  <Form.Control
                                    size="sm"
                                    type="text"
                                    placeholder="Summary of external research"
                                    value={researchSummary}
                                    onChange={(e) => setResearchSummary(e.target.value)}
                                  />
                                </Col>
                                <Col md={2}>
                                  <Button
                                    type="submit"
                                    className="btn-lb-primary w-100"
                                    size="sm"
                                  >
                                    Add Research
                                  </Button>
                                </Col>
                              </Row>
                            </Form>
                          )}
                        </Card.Body>
                      </Card>
                    </div>
                  )}

                  {/* TAB 2: EVIDENCE TIMELINE */}
                  {activeTab === 'timeline' && (
                    <Card className="soc-card">
                      <Card.Header className="soc-card-header py-3">
                        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
                          <div>
                            <div>
                              Evidence Timeline ({filteredTimeline.length} of{' '}
                              {activeProject.evidence_count})
                            </div>
                            <div className="small text-secondary fw-normal mt-1">
                              Click any timeline item to open full details, MITRE ATT&amp;CK mappings, analyst attribution, and screenshots.
                            </div>
                          </div>
                          <div className="d-flex flex-wrap align-items-center gap-2">
                            <Form.Check
                              type="switch"
                              id="key-only-switch"
                              label="Key Evidence Only"
                              checked={filterKeyOnly}
                              onChange={(e) => setFilterKeyOnly(e.target.checked)}
                              className="me-2 small text-lb-lime"
                            />
                            <Form.Select
                              size="sm"
                              style={{ width: '175px' }}
                              value={filterType}
                              onChange={(e) => setFilterType(e.target.value)}
                            >
                              <option value="ALL">All Types</option>
                              <option value="ATOMIC">Atomic Events</option>
                              <option value="SEARCH">Search Results</option>
                            </Form.Select>
                            <Form.Control
                              size="sm"
                              type="text"
                              placeholder="Filter timeline..."
                              style={{ width: '190px' }}
                              value={searchFilter}
                              onChange={(e) => setSearchFilter(e.target.value)}
                            />
                          </div>
                        </div>
                      </Card.Header>
                      <Card.Body className="p-0">
                        {filteredTimeline.length === 0 ? (
                          <div className="text-center py-5 text-secondary">
                            No evidence items recorded for this filter.
                          </div>
                        ) : (
                          <Table responsive hover variant="dark" className="mb-0 align-middle">
                            <thead className="small text-secondary text-uppercase">
                              <tr>
                                <th style={{ width: '95px' }}>Key</th>
                                <th style={{ width: '195px' }}>Timestamp (UTC)</th>
                                <th style={{ width: '210px' }}>Asset &amp; User</th>
                                <th>Summary &amp; Indicators</th>
                                <th style={{ width: '155px' }}>Links</th>
                                {canModifyActiveProject && (
                                  <th style={{ width: '100px' }} className="text-end">
                                    Actions
                                  </th>
                                )}
                              </tr>
                            </thead>
                            <tbody>
                              {filteredTimeline.map((item) => (
                                <tr
                                  key={item.id}
                                  onClick={() => setDetailEvidenceId(item.id)}
                                  title="Click to inspect full evidence details"
                                  className={`timeline-row-clickable ${
                                    item.is_key_evidence ? 'timeline-row-key' : ''
                                  }`}
                                >
                                  <td onClick={(e) => e.stopPropagation()}>
                                    {canModifyActiveProject ? (
                                      <Button
                                        variant={
                                          item.is_key_evidence
                                            ? 'outline-light'
                                            : 'outline-secondary'
                                        }
                                        size="sm"
                                        onClick={() => handleToggleKeyEvidence(item.id)}
                                        title="Toggle Key Evidence"
                                      >
                                        <Star
                                          size={14}
                                          fill={item.is_key_evidence ? '#9CEF69' : 'none'}
                                          color={item.is_key_evidence ? '#9CEF69' : '#94a3b8'}
                                          className="me-1"
                                        />
                                        <span
                                          className={item.is_key_evidence ? 'text-lb-lime' : ''}
                                        >
                                          {item.is_key_evidence ? 'Key' : 'Flag'}
                                        </span>
                                      </Button>
                                    ) : item.is_key_evidence ? (
                                      <span className="small text-lb-lime fw-semibold d-inline-flex align-items-center gap-1">
                                        <Star size={14} fill="#9CEF69" color="#9CEF69" />
                                        Key
                                      </span>
                                    ) : (
                                      <span className="text-secondary small">—</span>
                                    )}
                                  </td>

                                  <td className="mono-text small">
                                    <div className="text-white">
                                      {formatUtcTimestamp(item.timestamp)}
                                    </div>
                                    {item.evidence_type === 'SEARCH' && item.end_timestamp && (
                                      <div className="text-secondary mt-1">
                                        to {formatUtcTimestamp(item.end_timestamp)}
                                      </div>
                                    )}
                                  </td>

                                  <td className="mono-text small">
                                    <div>{defangText(item.affected_asset) || '—'}</div>
                                    <div className="text-secondary mt-1">
                                      {item.affected_user || '—'}
                                      {item.user_created_by_attacker && ' (Attacker-Created)'}
                                    </div>
                                  </td>

                                  <td className="small">
                                    {item.summary ? (
                                      <div className="fw-medium text-white mb-1">{item.summary}</div>
                                    ) : (
                                      <div className="text-secondary mb-1">No summary</div>
                                    )}
                                    {item.notes && (
                                      <div className="text-secondary mb-1">Notes: {item.notes}</div>
                                    )}
                                    {item.malicious_hosts_ips && (
                                      <div className="mono-text text-lb-cyan">
                                        Indicators: {defangText(item.malicious_hosts_ips)}
                                      </div>
                                    )}
                                  </td>

                                  {/* Analyst links to logs & searches are NOT defanged */}
                                  <td className="small" onClick={(e) => e.stopPropagation()}>
                                    <div className="d-flex flex-column gap-1">
                                      {item.related_log_link && (
                                        <a
                                          href={item.related_log_link}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="text-lb-cyan text-decoration-none"
                                        >
                                          Log/IDS Link <ExternalLink size={11} />
                                        </a>
                                      )}
                                      {item.search_result_link && (
                                        <a
                                          href={item.search_result_link}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="text-lb-cyan text-decoration-none"
                                        >
                                          Search Result <ExternalLink size={11} />
                                        </a>
                                      )}
                                      {item.search_query_link && (
                                        <a
                                          href={item.search_query_link}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="text-lb-cyan text-decoration-none"
                                        >
                                          Search Query <ExternalLink size={11} />
                                        </a>
                                      )}
                                      {!item.related_log_link &&
                                        !item.search_result_link &&
                                        !item.search_query_link && (
                                          <span className="text-secondary">—</span>
                                        )}
                                    </div>
                                  </td>

                                  {canModifyActiveProject && (
                                    <td className="text-end" onClick={(e) => e.stopPropagation()}>
                                      <div className="d-flex justify-content-end gap-1">
                                        <Button
                                          variant="outline-light"
                                          size="sm"
                                          title="Edit evidence item"
                                          onClick={() => openEditEvidenceModal(item)}
                                        >
                                          <Edit3 size={13} />
                                        </Button>
                                        <Button
                                          variant="outline-secondary"
                                          size="sm"
                                          title="Delete evidence item"
                                          onClick={() => handleDeleteEvidence(item.id)}
                                        >
                                          <Trash2 size={13} />
                                        </Button>
                                      </div>
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </Table>
                        )}
                      </Card.Body>
                    </Card>
                  )}

                  {/* TAB 3: INVESTIGATION REPORT GENERATION */}
                  {activeTab === 'reports' && (
                    <div className="d-flex flex-column gap-3">
                      <Row className="g-3">
                        <Col md={6}>
                          <Card className="soc-card h-100">
                            <Card.Header className="soc-card-header">
                              Report 1: Investigation Evidence Timeline (CSV)
                            </Card.Header>
                            <Card.Body className="d-flex flex-column justify-content-between">
                              <p className="small text-secondary mb-3">
                                Exports all {activeProject.evidence_count} investigation evidence
                                items in chronological order as a CSV file (
                                <code>date_customer_id_ticket_investigation_id.csv</code>, omitting
                                ticket if none is set), with defanged assets/indicators and MITRE
                                tactics and techniques.
                              </p>
                              <div>
                                <Button
                                  as="a"
                                  href={api.getCsvReportUrl(activeProject.id)}
                                  className="btn-lb-primary"
                                  size="sm"
                                >
                                  <FileSpreadsheet size={15} className="me-2" />
                                  Download Investigation CSV
                                </Button>
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>

                        <Col md={6}>
                          <Card className="soc-card h-100">
                            <Card.Header className="soc-card-header">
                              Report 2: Investigation Key Evidence Report (.ODT / .MD)
                            </Card.Header>
                            <Card.Body className="d-flex flex-column justify-content-between">
                              <p className="small text-secondary mb-3">
                                Exports only the {activeProject.key_evidence_count} Key Evidence
                                items from this investigation in chronological order, followed by
                                summary tables for Key Assets Affected, Key Malicious Indicators,
                                and MITRE Tactics &amp; Techniques.
                              </p>
                              <div className="d-flex flex-wrap gap-2">
                                <Button
                                  as="a"
                                  href={api.getOdtReportUrl(activeProject.id)}
                                  className="btn-lb-primary"
                                  size="sm"
                                >
                                  <FileText size={15} className="me-2" />
                                  Download Investigation (.ODT)
                                </Button>
                                <Button
                                  as="a"
                                  href={api.getMdZipReportUrl(activeProject.id)}
                                  className="btn-lb-cyan"
                                  size="sm"
                                >
                                  Download Markdown + Screenshots (.ZIP)
                                </Button>
                                <Button
                                  as="a"
                                  href={api.getMdReportUrl(activeProject.id)}
                                  variant="outline-light"
                                  size="sm"
                                >
                                  Download Investigation (.MD)
                                </Button>
                              </div>
                            </Card.Body>
                          </Card>
                        </Col>
                      </Row>

                      {/* Structured Key Evidence Report Preview */}
                      <Card className="soc-card">
                        <Card.Header className="soc-card-header">
                          Investigation Key Evidence Report Preview
                        </Card.Header>
                        <Card.Body className="d-flex flex-column gap-4">
                          {/* 1. TITLE & 2. Summary of Investigation */}
                          <div className="p-3 soc-subbox">
                            <h4 className="text-white fw-bold mb-2">
                              {activeProject.title || `Investigation #${activeProject.id}`}
                            </h4>
                            <div className="text-lb-cyan small fw-semibold mb-1">
                              Summary of Investigation
                            </div>
                            <div>
                              {activeProject.summary || 'No summary of investigation recorded.'}
                            </div>
                          </div>

                          {/* 3. Key Evidence Timeline */}
                          <div>
                            <h6 className="text-lb-cyan fw-semibold mb-3">
                              Key Evidence Timeline ({keyEvidenceItems.length})
                            </h6>
                            {keyEvidenceItems.length === 0 ? (
                              <div className="text-secondary small">
                                No items flagged as Key Evidence yet.
                              </div>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {keyEvidenceItems.map((item) => {
                                  const tsDisplay =
                                    item.evidence_type === 'SEARCH' && item.end_timestamp
                                      ? `${formatUtcTimestamp(item.timestamp)} - ${formatUtcTimestamp(item.end_timestamp)}`
                                      : formatUtcTimestamp(item.timestamp);
                                  const assetDisplay = defangText(item.affected_asset) || 'N/A';
                                  const userDisplay = item.affected_user
                                    ? `${item.affected_user}${item.user_created_by_attacker ? ' (Created by Attacker)' : ''}`
                                    : 'N/A';
                                  const notesDisplay = [item.summary, item.notes]
                                    .filter(Boolean)
                                    .join(' — ');
                                  const itemIndicators = parseItems(
                                    item.malicious_hosts_ips,
                                    item.commands_run
                                      ? item.commands_run
                                          .split('\n')
                                          .filter(Boolean)
                                          .map((c) => `Command: ${defangText(c)}`)
                                      : [],
                                    true,
                                  );
                                  const links = [
                                    item.related_log_link,
                                    item.search_result_link,
                                    item.search_query_link,
                                  ].filter(Boolean);

                                  return (
                                    <div key={item.id} className="p-3 soc-subbox">
                                      <div className="fw-bold mono-text text-white mb-2 pb-1 border-bottom border-secondary">
                                        {tsDisplay}, {assetDisplay}, {userDisplay}:
                                      </div>

                                      <div className="small mb-2">
                                        <strong>Analyst notes:</strong> {notesDisplay || 'None'}
                                      </div>

                                      <div className="small mb-2">
                                        <strong>Key malicious indicators:</strong>
                                        {itemIndicators.length === 0 ? (
                                          <span className="ms-1 text-secondary">None</span>
                                        ) : (
                                          <ul className="bullet-list mono-text mt-1">
                                            {itemIndicators.map((ind, i) => (
                                              <li key={i}>{ind}</li>
                                            ))}
                                          </ul>
                                        )}
                                      </div>

                                      <div className="small mb-2">
                                        <strong>Screenshot:</strong>
                                        {item.screenshots && item.screenshots.length > 0 ? (
                                          <div className="d-flex flex-wrap gap-2 mt-1">
                                            {item.screenshots.map((shot) => (
                                              <img
                                                key={shot.id}
                                                src={shot.image_url}
                                                alt={shot.caption || shot.filename}
                                                className="screenshot-thumb"
                                                onClick={() => setPreviewScreenshot(shot)}
                                              />
                                            ))}
                                          </div>
                                        ) : (
                                          <span className="ms-1 text-secondary">None</span>
                                        )}
                                      </div>

                                      <div className="small">
                                        <strong>Links:</strong>{' '}
                                        {links.length > 0 ? (
                                          links.map((l, idx) => (
                                            <React.Fragment key={idx}>
                                              {idx > 0 && ' , '}
                                              <a
                                                href={l}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-lb-cyan mono-text text-decoration-none"
                                              >
                                                {l} <ExternalLink size={11} />
                                              </a>
                                            </React.Fragment>
                                          ))
                                        ) : (
                                          <span className="text-secondary">None</span>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>

                          {/* 4. Investigation Summary Tables at the Bottom */}
                          <div>
                            <h6 className="text-lb-cyan fw-semibold mb-3">
                              Investigation Summary Tables (Bottom of Report)
                            </h6>
                            <Row className="g-3">
                              <Col md={6}>
                                <Table bordered size="sm" variant="dark" className="mono-text mb-0">
                                  <thead>
                                    <tr>
                                      <th className="text-lb-cyan">Key Assets Affected</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {assetList.length === 0 ? (
                                      <tr>
                                        <td className="text-secondary">None recorded</td>
                                      </tr>
                                    ) : (
                                      assetList.map((a, i) => (
                                        <tr key={i}>
                                          <td>{a}</td>
                                        </tr>
                                      ))
                                    )}
                                  </tbody>
                                </Table>
                              </Col>

                              <Col md={6}>
                                <Table bordered size="sm" variant="dark" className="mono-text mb-0">
                                  <thead>
                                    <tr>
                                      <th className="text-lb-cyan">Key Malicious Indicators</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {indicatorList.length === 0 ? (
                                      <tr>
                                        <td className="text-secondary">None recorded</td>
                                      </tr>
                                    ) : (
                                      indicatorList.map((ind, i) => (
                                        <tr key={i}>
                                          <td>{ind}</td>
                                        </tr>
                                      ))
                                    )}
                                  </tbody>
                                </Table>
                              </Col>

                              <Col md={12}>
                                <Table bordered size="sm" variant="dark" className="mono-text mb-0">
                                  <thead>
                                    <tr>
                                      <th className="text-lb-cyan">MITRE Tactic</th>
                                      <th className="text-lb-cyan">MITRE Technique</th>
                                      <th className="text-lb-cyan">Affected Assets</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {!activeProject.mitre_summary ||
                                    activeProject.mitre_summary.length === 0 ? (
                                      <tr>
                                        <td colSpan={3} className="text-secondary">
                                          No MITRE tactics or techniques recorded
                                        </td>
                                      </tr>
                                    ) : (
                                      activeProject.mitre_summary.map((row, idx) => (
                                        <tr key={idx}>
                                          <td>{row.tactic}</td>
                                          <td>{row.technique}</td>
                                          <td>
                                            {row.assets && row.assets.length > 0
                                              ? row.assets.join(', ')
                                              : '—'}
                                          </td>
                                        </tr>
                                      ))
                                    )}
                                  </tbody>
                                </Table>
                              </Col>
                            </Row>
                          </div>
                        </Card.Body>
                      </Card>
                    </div>
                  )}
                </>
              )}
            </Col>
          </Row>
        )}
      </Container>

      {/* Warning Modal when Closing / Archiving an Investigation */}
      <Modal
        show={showArchiveWarningModal}
        onHide={() => {
          setShowArchiveWarningModal(false);
          setPendingArchiveAction(null);
        }}
        transition={false}
        centered
      >
        <Modal.Header closeButton className="bg-dark border-warning">
          <Modal.Title className="fs-6 d-flex align-items-center gap-2 text-warning">
            <AlertTriangle size={18} />
            <span>Confirm Closing / Archiving Investigation</span>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-dark text-light small">
          <p className="mb-2">
            Are you sure you want to mark this investigation as{' '}
            <strong>Archived / Closed</strong>?
          </p>
          <p className="text-secondary mb-0">
            Archived investigations are hidden from the sidebar by default. You can still view and
            re-open them anytime by enabling the <strong>Show Archived</strong> toggle in the
            investigations sidebar.
          </p>
        </Modal.Body>
        <Modal.Footer className="bg-dark border-secondary">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => {
              setShowArchiveWarningModal(false);
              setPendingArchiveAction(null);
            }}
          >
            Cancel
          </Button>
          <Button variant="warning" size="sm" onClick={confirmArchiveAction}>
            Archive / Close Investigation
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal: Confirm Delete Investigation (Admin / Super Admin) */}
      <Modal
        show={showDeleteProjectModal}
        onHide={() => setShowDeleteProjectModal(false)}
        transition={false}
        centered
      >
        <Modal.Header closeButton className="bg-dark border-danger">
          <Modal.Title className="fs-6 d-flex align-items-center gap-2 text-danger">
            <AlertTriangle size={18} />
            <span>Confirm Investigation Deletion</span>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-dark text-light small">
          <p className="mb-2">
            Permanently delete investigation{' '}
            <strong>{activeProject?.title || `#${activeProject?.id}`}</strong>?
          </p>
          <p className="text-secondary mb-0">
            This removes the investigation, all timeline evidence items, external research entries,
            and its associated artifact directory on disk. This action cannot be undone.
          </p>
        </Modal.Body>
        <Modal.Footer className="bg-dark border-secondary">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => setShowDeleteProjectModal(false)}
          >
            Cancel
          </Button>
          <Button variant="danger" size="sm" onClick={handleConfirmDeleteProject}>
            Delete Investigation Permanently
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal: Create / Edit Investigation Overview */}
      <Modal
        show={showProjectModal}
        onHide={() => setShowProjectModal(false)}
        size="lg"
        transition={false}
        centered
      >
        <Form onSubmit={handleSaveProject}>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="fs-6">
              {editingProject ? 'Edit Investigation Overview' : 'New Investigation'}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark">
            <Row className="g-3">
              <Col md={8}>
                <Form.Group>
                  <Form.Label className="small">Title</Form.Label>
                  <Form.Control
                    type="text"
                    value={projectForm.title}
                    onChange={(e) => setProjectForm({ ...projectForm, title: e.target.value })}
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">Status</Form.Label>
                  <Form.Select
                    value={projectForm.status}
                    onChange={(e) => setProjectForm({ ...projectForm, status: e.target.value })}
                  >
                    <option value="OPEN">Open / Triage</option>
                    <option value="INVESTIGATING">Investigating</option>
                    <option value="CONTAINED">Contained</option>
                    <option value="ARCHIVED">Archived / Closed</option>
                  </Form.Select>
                </Form.Group>
              </Col>

              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Customer Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={projectForm.customer_name}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, customer_name: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Customer ID</Form.Label>
                  <Form.Control
                    type="text"
                    value={projectForm.customer_id}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, customer_id: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">Ticket ID</Form.Label>
                  <Form.Control
                    type="text"
                    value={projectForm.ticket_id}
                    onChange={(e) => setProjectForm({ ...projectForm, ticket_id: e.target.value })}
                  />
                </Form.Group>
              </Col>
              <Col md={8}>
                <Form.Group>
                  <Form.Label className="small">Ticket Link</Form.Label>
                  <Form.Control
                    type="text"
                    value={projectForm.ticket_link}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, ticket_link: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">Summary of Investigation</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    value={projectForm.summary}
                    onChange={(e) => setProjectForm({ ...projectForm, summary: e.target.value })}
                  />
                </Form.Group>
              </Col>

              <Col md={7}>
                <Form.Group>
                  <Form.Label className="small">
                    Action Plan (Next steps, areas to investigate, customer info needed)
                  </Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={projectForm.action_plan}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, action_plan: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={5}>
                <Form.Group>
                  <Form.Label className="small">
                    Customer Bridge / Escalation Notes (Optional)
                  </Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    placeholder="e.g. 24/7 SOC Bridge +1-555-0199; individual contacts can be added in Overview"
                    value={projectForm.key_customer_contacts}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, key_customer_contacts: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">Key Assets Affected (one per line)</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={projectForm.key_assets_affected}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, key_assets_affected: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">Key Users Affected (one per line)</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={projectForm.key_users_affected}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, key_users_affected: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">
                    Key Malicious Indicators (one per line)
                  </Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={projectForm.key_malicious_indicators}
                    onChange={(e) =>
                      setProjectForm({ ...projectForm, key_malicious_indicators: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              {!editingProject && (
                <>
                  <Col md={5}>
                    <Form.Group>
                      <Form.Label className="small">
                        Initial External Research Link (Optional)
                      </Form.Label>
                      <Form.Control
                        type="text"
                        value={projectForm.external_research_link}
                        onChange={(e) =>
                          setProjectForm({
                            ...projectForm,
                            external_research_link: e.target.value,
                          })
                        }
                      />
                    </Form.Group>
                  </Col>
                  <Col md={7}>
                    <Form.Group>
                      <Form.Label className="small">
                        Initial External Research Summary (Optional)
                      </Form.Label>
                      <Form.Control
                        type="text"
                        value={projectForm.external_research_summary}
                        onChange={(e) =>
                          setProjectForm({
                            ...projectForm,
                            external_research_summary: e.target.value,
                          })
                        }
                      />
                    </Form.Group>
                  </Col>
                </>
              )}
            </Row>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" onClick={() => setShowProjectModal(false)}>
              Cancel
            </Button>
            <Button className={editingProject ? 'btn-lb-primary' : 'btn-lb-green'} type="submit">
              {editingProject ? 'Save Investigation' : 'New Investigation'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Modal: Add / Edit Evidence Item */}
      <Modal
        show={showEvidenceModal}
        onHide={() => setShowEvidenceModal(false)}
        size="lg"
        transition={false}
        centered
      >
        <Form onSubmit={handleSaveEvidence}>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="fs-6">
              {editingEvidenceId ? 'Edit Evidence' : 'Add Evidence'}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark">
            <Row className="g-3">
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Evidence Type</Form.Label>
                  <Form.Select
                    value={evidenceForm.evidence_type}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, evidence_type: e.target.value })
                    }
                  >
                    <option value="ATOMIC">Atomic Event (Single IDS / Log Event)</option>
                    <option value="SEARCH">Search Result (Activity Pattern Over Time)</option>
                  </Form.Select>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Analyst</Form.Label>
                  <Form.Control
                    type="text"
                    list="soc-analysts-list"
                    value={evidenceForm.analyst_name}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, analyst_name: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={evidenceForm.evidence_type === 'SEARCH' ? 6 : 12}>
                <Form.Group>
                  <Form.Label className="small">
                    {evidenceForm.evidence_type === 'SEARCH'
                      ? 'Start Timestamp (UTC)'
                      : 'Timestamp (UTC)'}
                  </Form.Label>
                  <Form.Control
                    type="datetime-local"
                    step="1"
                    value={evidenceForm.timestamp}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, timestamp: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>
              {evidenceForm.evidence_type === 'SEARCH' && (
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="small">End Timestamp (UTC)</Form.Label>
                    <Form.Control
                      type="datetime-local"
                      step="1"
                      value={evidenceForm.end_timestamp}
                      onChange={(e) =>
                        setEvidenceForm({ ...evidenceForm, end_timestamp: e.target.value })
                      }
                    />
                  </Form.Group>
                </Col>
              )}

              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Affected Asset</Form.Label>
                  <Form.Control
                    type="text"
                    value={evidenceForm.affected_asset}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, affected_asset: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Affected User</Form.Label>
                  <Form.Control
                    type="text"
                    value={evidenceForm.affected_user}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, affected_user: e.target.value })
                    }
                  />
                  <Form.Check
                    type="checkbox"
                    id="attacker-created-user-check"
                    className="mt-1 small text-secondary"
                    label="Created by attacker"
                    checked={evidenceForm.user_created_by_attacker}
                    onChange={(e) =>
                      setEvidenceForm({
                        ...evidenceForm,
                        user_created_by_attacker: e.target.checked,
                      })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">Summary of Evidence</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    value={evidenceForm.summary}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, summary: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">
                    Malicious Hosts / IPs / Domains Involved
                  </Form.Label>
                  <Form.Control
                    type="text"
                    value={evidenceForm.malicious_hosts_ips}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, malicious_hosts_ips: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">Commands Run</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    className="mono-text"
                    value={evidenceForm.commands_run}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, commands_run: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>

              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">MITRE Tactics (Multi-Select)</Form.Label>
                  <MitreTacticsSelect
                    value={evidenceForm.mitre_tactic}
                    onChange={(nextTactics) =>
                      setEvidenceForm((prev) => ({ ...prev, mitre_tactic: nextTactics }))
                    }
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">MITRE Techniques (Multi-Select)</Form.Label>
                  <MitreTechniquesSelect
                    tacticValue={evidenceForm.mitre_tactic}
                    value={evidenceForm.mitre_technique}
                    onChange={(nextTechniques) =>
                      setEvidenceForm((prev) => ({ ...prev, mitre_technique: nextTechniques }))
                    }
                    onAutoAddTactic={(nextTactics) =>
                      setEvidenceForm((prev) => ({ ...prev, mitre_tactic: nextTactics }))
                    }
                  />
                </Form.Group>
              </Col>

              {evidenceForm.evidence_type === 'ATOMIC' ? (
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="small">Link to Related Log / IDS Event</Form.Label>
                    <Form.Control
                      type="text"
                      value={evidenceForm.related_log_link}
                      onChange={(e) =>
                        setEvidenceForm({ ...evidenceForm, related_log_link: e.target.value })
                      }
                    />
                  </Form.Group>
                </Col>
              ) : (
                <>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="small">Search Result Link</Form.Label>
                      <Form.Control
                        type="text"
                        value={evidenceForm.search_result_link}
                        onChange={(e) =>
                          setEvidenceForm({
                            ...evidenceForm,
                            search_result_link: e.target.value,
                          })
                        }
                      />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group>
                      <Form.Label className="small">Search Query Link</Form.Label>
                      <Form.Control
                        type="text"
                        value={evidenceForm.search_query_link}
                        onChange={(e) =>
                          setEvidenceForm({
                            ...evidenceForm,
                            search_query_link: e.target.value,
                          })
                        }
                      />
                    </Form.Group>
                  </Col>
                </>
              )}

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">Freeform Notes</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    value={evidenceForm.notes}
                    onChange={(e) => setEvidenceForm({ ...evidenceForm, notes: e.target.value })}
                  />
                </Form.Group>
              </Col>

              {/* Existing Attached Screenshots when Editing */}
              {currentlyEditingItem &&
                currentlyEditingItem.screenshots &&
                currentlyEditingItem.screenshots.length > 0 && (
                  <Col md={12}>
                    <div className="small mb-2">Attached Screenshots</div>
                    <div className="d-flex flex-wrap gap-3 p-2 soc-subbox">
                      {currentlyEditingItem.screenshots.map((shot) => (
                        <div key={shot.id} className="d-flex align-items-center gap-2">
                          <img
                            src={shot.image_url}
                            alt={shot.caption || shot.filename}
                            className="screenshot-thumb"
                            onClick={() => setPreviewScreenshot(shot)}
                          />
                          <Button
                            variant="outline-danger"
                            size="sm"
                            onClick={() => handleDeleteScreenshot(shot.id)}
                          >
                            <Trash2 size={13} className="me-1" />
                            Delete
                          </Button>
                        </div>
                      ))}
                    </div>
                  </Col>
                )}

              <Col md={7}>
                <Form.Group>
                  <Form.Label className="small">Add Screenshots</Form.Label>
                  <Form.Control
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={(e) => setScreenshotFiles(Array.from(e.target.files || []))}
                  />
                </Form.Group>
              </Col>
              <Col md={5}>
                <Form.Group>
                  <Form.Label className="small">Screenshot Caption</Form.Label>
                  <Form.Control
                    type="text"
                    value={screenshotCaption}
                    onChange={(e) => setScreenshotCaption(e.target.value)}
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Check
                  type="switch"
                  id="key-evidence-flag-modal"
                  label="Flag as Key Evidence for Report"
                  checked={evidenceForm.is_key_evidence}
                  onChange={(e) =>
                    setEvidenceForm({ ...evidenceForm, is_key_evidence: e.target.checked })
                  }
                />
              </Col>
            </Row>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" onClick={() => setShowEvidenceModal(false)}>
              Cancel
            </Button>
            <Button className="btn-lb-primary" type="submit">
              Save Evidence
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Modal: Full Evidence Item Details Popup (opened on timeline row click) */}
      <EvidenceDetailModal
        item={detailEvidenceItem}
        show={Boolean(detailEvidenceItem)}
        onHide={() => setDetailEvidenceId(null)}
        defangText={defangText}
        canModifyActiveProject={canModifyActiveProject}
        onToggleKey={handleToggleKeyEvidence}
        onEdit={openEditEvidenceModal}
        onDelete={handleDeleteEvidence}
        onPreviewScreenshot={(shot) => setPreviewScreenshot(shot)}
        onDeleteScreenshot={handleDeleteScreenshot}
      />

      {/* Modal: Screenshot Preview */}
      <Modal
        show={Boolean(previewScreenshot)}
        onHide={() => setPreviewScreenshot(null)}
        size="lg"
        transition={false}
        centered
      >
        <Modal.Header closeButton className="bg-dark border-secondary">
          <Modal.Title className="fs-6">
            {previewScreenshot?.caption || previewScreenshot?.filename}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-dark text-center">
          {previewScreenshot && (
            <img
              src={previewScreenshot.image_url}
              alt={previewScreenshot.caption || previewScreenshot.filename}
              className="img-fluid rounded border border-secondary"
            />
          )}
        </Modal.Body>
        <Modal.Footer className="bg-dark border-secondary justify-content-between">
          <div>
            {previewScreenshot && canModifyActiveProject && (
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => handleDeleteScreenshot(previewScreenshot.id)}
              >
                <Trash2 size={14} className="me-1" />
                Delete Screenshot
              </Button>
            )}
          </div>
          <Button variant="outline-secondary" size="sm" onClick={() => setPreviewScreenshot(null)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal: Create / Edit User Account (Admin & Super Admin) */}
      <Modal
        show={showUserModal}
        onHide={() => setShowUserModal(false)}
        transition={false}
        centered
      >
        <Form onSubmit={handleSaveUser}>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="fs-6">
              {editingUserObj
                ? `Edit User: ${editingUserObj.username}`
                : 'Create New User Account'}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark">
            <Row className="g-3">
              {!editingUserObj && (
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="small">Username</Form.Label>
                    <Form.Control
                      type="text"
                      required
                      value={userForm.username}
                      onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                    />
                  </Form.Group>
                </Col>
              )}

              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">First Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={userForm.first_name}
                    onChange={(e) => setUserForm({ ...userForm, first_name: e.target.value })}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Last Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={userForm.last_name}
                    onChange={(e) => setUserForm({ ...userForm, last_name: e.target.value })}
                  />
                </Form.Group>
              </Col>

              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Email</Form.Label>
                  <Form.Control
                    type="email"
                    value={userForm.email}
                    onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  />
                </Form.Group>
              </Col>

              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">Profile Role / Job Title</Form.Label>
                  <Form.Control
                    type="text"
                    placeholder="e.g. Senior SOC Analyst"
                    value={userForm.job_role}
                    onChange={(e) => setUserForm({ ...userForm, job_role: e.target.value })}
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">System Access Role</Form.Label>
                  <Form.Select
                    value={userForm.role}
                    onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                  >
                    {assignableRoles.map(([code, label]) => (
                      <option key={code} value={code}>
                        {label}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              </Col>

              {!editingUserObj && (
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="small">Initial Password</Form.Label>
                    <Form.Control
                      type="password"
                      required
                      value={userForm.password}
                      onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                    />
                  </Form.Group>
                </Col>
              )}

              <Col md={12}>
                <Form.Check
                  type="switch"
                  id="user-active-switch"
                  label="Account Active (allowed to sign in)"
                  checked={userForm.is_active}
                  onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })}
                />
              </Col>
            </Row>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="outline-secondary" size="sm" onClick={() => setShowUserModal(false)}>
              Cancel
            </Button>
            <Button className="btn-lb-primary" size="sm" type="submit">
              {editingUserObj ? 'Save Changes' : 'Create User'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Modal: Reset User Password (Admin & Super Admin) */}
      <Modal
        show={Boolean(resetTargetUser)}
        onHide={() => setResetTargetUser(null)}
        transition={false}
        centered
      >
        <Form onSubmit={handleConfirmPasswordReset}>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="fs-6">
              Reset Password for {resetTargetUser?.username}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark">
            <p className="small text-secondary mb-3">
              Enter a new password for <strong>{resetTargetUser?.username}</strong> (
              {ROLE_LABELS[resetTargetUser?.role] || resetTargetUser?.role}). Active sessions and
              API tokens for this user will be invalidated.
            </p>
            <Form.Group>
              <Form.Label className="small">New Password</Form.Label>
              <Form.Control
                type="password"
                required
                autoFocus
                value={resetNewPassword}
                onChange={(e) => setResetNewPassword(e.target.value)}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={() => setResetTargetUser(null)}
            >
              Cancel
            </Button>
            <Button className="btn-lb-primary" size="sm" type="submit">
              Reset Password
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Modal: Confirm Delete User */}
      <Modal
        show={Boolean(deleteTargetUser)}
        onHide={() => setDeleteTargetUser(null)}
        transition={false}
        centered
      >
        <Modal.Header closeButton className="bg-dark border-danger">
          <Modal.Title className="fs-6 text-danger">Confirm User Deletion</Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-dark text-light small">
          Are you sure you want to permanently delete user{' '}
          <strong>{deleteTargetUser?.username}</strong>?
        </Modal.Body>
        <Modal.Footer className="bg-dark border-secondary">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => setDeleteTargetUser(null)}
          >
            Cancel
          </Button>
          <Button variant="danger" size="sm" onClick={handleConfirmDeleteUser}>
            Delete User
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal: Self Account, Avatar, Display Name, Pronouns, Password & SOC API Token */}
      <AccountProfileModal
        show={showAccountModal}
        onHide={() => setShowAccountModal(false)}
        authUser={authUser}
        roleLabel={ROLE_LABELS[authUser.role] || authUser.role}
        canEditRole={canEditRole}
        onProfileUpdated={handleProfileUpdated}
        onNotifySuccess={notifySuccess}
        onApiError={handleApiError}
      />
    </div>
  );
}
