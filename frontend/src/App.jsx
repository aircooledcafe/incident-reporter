import React, { useState, useEffect } from 'react';
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
  InputGroup,
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
  X,
  AlertTriangle,
  ChevronDown,
} from 'lucide-react';
import { api } from './api';

const STATUS_LABELS = {
  OPEN: 'Open / Triage',
  INVESTIGATING: 'Investigating',
  CONTAINED: 'Contained',
  ARCHIVED: 'Archived / Closed',
};

const EMPTY_PROJECT_FORM = {
  title: '',
  customer_name: '',
  customer_id: '',
  ticket_id: '',
  ticket_link: '',
  summary: '',
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
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [activeProject, setActiveProject] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'timeline' | 'reports'
  const [currentAnalyst, setCurrentAnalyst] = useState('Chrisjen Avasarala');

  // Sidebar Archived/Closed filter (hidden by default)
  const [showArchivedSidebar, setShowArchivedSidebar] = useState(false);

  // Header status picker & Archive warning modal state
  const [showHeaderStatusPicker, setShowHeaderStatusPicker] = useState(false);
  const [showArchiveWarningModal, setShowArchiveWarningModal] = useState(false);
  const [pendingArchiveAction, setPendingArchiveAction] = useState(null);

  const [loading, setLoading] = useState(true);
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

  // Screenshot Lightbox Modal
  const [previewScreenshot, setPreviewScreenshot] = useState(null);

  // Timeline filters
  const [filterKeyOnly, setFilterKeyOnly] = useState(false);
  const [filterType, setFilterType] = useState('ALL');
  const [searchFilter, setSearchFilter] = useState('');

  const notifySuccess = useEventCallback((msg) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 3500);
  });

  const loadProjects = useEventCallback(async (selectId = null) => {
    try {
      setLoading(true);
      const list = await api.listProjects();
      setProjects(list);
      const nonArchived = list.filter((p) => p.status !== 'ARCHIVED');
      const defaultFirst = nonArchived[0] || list[0];
      const targetId = selectId || selectedProjectId || (defaultFirst && defaultFirst.id);
      if (targetId) {
        const detail = await api.getProject(targetId);
        setSelectedProjectId(detail.id);
        setActiveProject(detail);
      } else {
        setSelectedProjectId(null);
        setActiveProject(null);
      }
    } catch (err) {
      setErrorMsg(`Failed to load incident projects: ${err.message}`);
    } finally {
      setLoading(false);
    }
  });

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleSelectProject = useEventCallback(async (id) => {
    try {
      setLoading(true);
      setShowHeaderStatusPicker(false);
      const detail = await api.getProject(id);
      setSelectedProjectId(detail.id);
      setActiveProject(detail);
    } catch (err) {
      setErrorMsg(`Could not load project #${id}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  });

  const handleSeedDemo = useEventCallback(async () => {
    try {
      setLoading(true);
      const created = await api.seedDemoProject();
      await loadProjects(created.id);
      notifySuccess('Demo incident loaded (20 total events, 7 Key Evidence events).');
    } catch (err) {
      setErrorMsg(`Failed to load sample project: ${err.message}`);
    } finally {
      setLoading(false);
    }
  });

  const applyStatusUpdate = async (newStatus) => {
    if (!activeProject) return;
    try {
      const updated = await api.updateProject(activeProject.id, { status: newStatus });
      setActiveProject(updated);
      await loadProjects(updated.id);
      setShowHeaderStatusPicker(false);
      notifySuccess(`Project status updated to ${STATUS_LABELS[newStatus] || newStatus}.`);
    } catch (err) {
      setErrorMsg(`Failed to update status: ${err.message}`);
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
      lead_analyst: currentAnalyst,
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
      key_assets_affected: activeProject.key_assets_affected || '',
      key_users_affected: activeProject.key_users_affected || '',
      key_malicious_indicators: activeProject.key_malicious_indicators || '',
      external_research_link: '',
      external_research_summary: '',
      status: activeProject.status || 'INVESTIGATING',
      lead_analyst: activeProject.lead_analyst || currentAnalyst,
    });
    setShowProjectModal(true);
  };

  const executeSaveProject = async () => {
    try {
      if (editingProject && activeProject) {
        const updated = await api.updateProject(activeProject.id, projectForm);
        setActiveProject(updated);
        await loadProjects(updated.id);
        notifySuccess('Project overview updated.');
      } else {
        const created = await api.createProject(projectForm);
        await loadProjects(created.id);
        notifySuccess(`Created project "${created.title || '#' + created.id}".`);
      }
      setShowProjectModal(false);
    } catch (err) {
      setErrorMsg(`Failed to save project: ${err.message}`);
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
      analyst_name: currentAnalyst,
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
      analyst_name: item.analyst_name || currentAnalyst,
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
      formData.append('analyst_name', evidenceForm.analyst_name || currentAnalyst);

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
      setErrorMsg(`Failed to save evidence: ${err.message}`);
    }
  };

  const handleToggleKeyEvidence = async (itemId) => {
    if (!activeProject) return;
    try {
      await api.toggleKeyEvidence(itemId);
      await handleSelectProject(activeProject.id);
    } catch (err) {
      setErrorMsg(`Could not toggle key evidence flag: ${err.message}`);
    }
  };

  const handleDeleteEvidence = async (itemId) => {
    if (!activeProject) return;
    try {
      await api.deleteEvidence(itemId);
      await handleSelectProject(activeProject.id);
      notifySuccess('Evidence item deleted.');
    } catch (err) {
      setErrorMsg(`Failed to delete evidence: ${err.message}`);
    }
  };

  const handleDeleteScreenshot = async (screenshotId) => {
    if (!activeProject) return;
    try {
      await api.deleteScreenshot(screenshotId);
      if (previewScreenshot && previewScreenshot.id === screenshotId) {
        setPreviewScreenshot(null);
      }
      await handleSelectProject(activeProject.id);
      notifySuccess('Screenshot deleted from event.');
    } catch (err) {
      setErrorMsg(`Failed to delete screenshot: ${err.message}`);
    }
  };

  const handleAddExternalResearch = async (e) => {
    e.preventDefault();
    if (!activeProject || (!researchLink.trim() && !researchSummary.trim())) return;
    try {
      await api.addExternalResearch({
        project: activeProject.id,
        link: researchLink.trim(),
        summary: researchSummary.trim(),
        analyst_name: currentAnalyst,
      });
      setResearchLink('');
      setResearchSummary('');
      await handleSelectProject(activeProject.id);
      notifySuccess('External research added.');
    } catch (err) {
      setErrorMsg(`Could not add external research: ${err.message}`);
    }
  };

  const handleDeleteExternalResearch = async (id) => {
    if (!activeProject) return;
    try {
      await api.deleteExternalResearch(id);
      await handleSelectProject(activeProject.id);
      notifySuccess('External research item removed.');
    } catch (err) {
      setErrorMsg(`Failed to delete research entry: ${err.message}`);
    }
  };

  const handleClearLegacyInlineResearch = async () => {
    if (!activeProject) return;
    try {
      await api.updateProject(activeProject.id, {
        external_research_link: '',
        external_research_summary: '',
      });
      await handleSelectProject(activeProject.id);
      notifySuccess('External research item removed.');
    } catch (err) {
      setErrorMsg(`Failed to remove research item: ${err.message}`);
    }
  };

  // Sidebar projects filtering (hide ARCHIVED by default unless showArchivedSidebar is enabled)
  const archivedCount = projects.filter((p) => p.status === 'ARCHIVED').length;
  const visibleSidebarProjects = projects.filter(
    (p) => showArchivedSidebar || p.status !== 'ARCHIVED',
  );

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

  return (
    <div className="min-vh-100 d-flex flex-column">
      {/* Datalist for Analyst suggestions */}
      <datalist id="soc-analysts-list">
        <option value="Chrisjen Avasarala" />
        <option value="James Holden" />
      </datalist>

      {/* Top Navigation Bar */}
      <Navbar className="soc-navbar py-2 px-3" variant="dark" expand="lg">
        <Container fluid>
          <Navbar.Brand className="fw-semibold text-white">
            Incident Response Evidence Recorder
          </Navbar.Brand>

          <div className="d-flex align-items-center gap-2 ms-auto">
            <InputGroup size="sm" style={{ width: '280px' }}>
              <InputGroup.Text className="bg-dark text-secondary border-secondary">
                Analyst
              </InputGroup.Text>
              <Form.Control
                type="text"
                list="soc-analysts-list"
                value={currentAnalyst}
                onChange={(e) => setCurrentAnalyst(e.target.value)}
                placeholder="Chrisjen Avasarala / James Holden"
                className="bg-dark text-light border-secondary"
              />
            </InputGroup>
            <Button className="btn-lb-cyan" size="sm" onClick={handleSeedDemo}>
              Load Sample Incident
            </Button>
            <Button className="btn-lb-primary" size="sm" onClick={openNewProjectModal}>
              <Plus size={15} className="me-1" />
              New Project
            </Button>
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

        <Row className="g-4">
          {/* Left Sidebar: Projects List */}
          <Col lg={3} xl={2}>
            <Card className="soc-card">
              <Card.Header className="soc-card-header py-2">
                <div className="d-flex justify-content-between align-items-center">
                  <span className="small text-uppercase text-secondary">
                    Projects ({visibleSidebarProjects.length})
                  </span>
                </div>
                <div className="mt-2 pt-1 border-top border-secondary">
                  <Form.Check
                    type="switch"
                    id="show-archived-switch"
                    label={`Show Archived (${archivedCount})`}
                    checked={showArchivedSidebar}
                    onChange={(e) => setShowArchivedSidebar(e.target.checked)}
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
                        ? 'No active investigations. Toggle "Show Archived" above to view closed projects.'
                        : 'No projects created yet.'}
                    </p>
                    <Button className="btn-lb-primary w-100" size="sm" onClick={openNewProjectModal}>
                      Create Project
                    </Button>
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
                              {p.title || `Incident #${p.id}`}
                            </div>
                          </div>
                          <div className="mt-1 mb-1">
                            <Badge
                              bg={p.status === 'ARCHIVED' ? 'secondary' : 'dark'}
                              className="border border-secondary text-lb-cyan fw-normal"
                              style={{ fontSize: '0.68rem' }}
                            >
                              {STATUS_LABELS[p.status] || p.status}
                            </Badge>
                          </div>
                          <div className="text-secondary" style={{ fontSize: '0.75rem' }}>
                            <div>{p.customer_name || 'No Customer'}</div>
                            <div>
                              {p.ticket_id || 'No Ticket'} &bull; {p.evidence_count} events ({p.key_evidence_count} key)
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

          {/* Main Project Area */}
          <Col lg={9} xl={10}>
            {!activeProject ? (
              <Card className="soc-card text-center py-5">
                <Card.Body>
                  <h5 className="text-white mb-2">Select or Create an Incident Project</h5>
                  <p className="text-secondary small mb-3">
                    Create a new incident project or load the sample incident to begin recording evidence.
                  </p>
                  <div className="d-flex justify-content-center gap-2">
                    <Button className="btn-lb-primary" onClick={openNewProjectModal}>
                      Create Project
                    </Button>
                    <Button className="btn-lb-cyan" onClick={handleSeedDemo}>
                      Load Sample Incident
                    </Button>
                  </div>
                </Card.Body>
              </Card>
            ) : (
              <>
                {/* Project Header */}
                <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                  <div>
                    <h4 className="mb-1 text-white fw-semibold">
                      {activeProject.title || `Incident #${activeProject.id}`}
                    </h4>
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

                      {/* Clickable Status Picker in Header */}
                      <div className="position-relative d-inline-block">
                        <button
                          type="button"
                          onClick={() => setShowHeaderStatusPicker((prev) => !prev)}
                          className="btn btn-sm btn-outline-light py-1 px-2 d-inline-flex align-items-center gap-1"
                          style={{ fontSize: '0.78rem' }}
                          title="Click to change investigation status"
                        >
                          <span>
                            Status: <strong>{STATUS_LABELS[activeProject.status] || activeProject.status}</strong>
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
                    </div>
                  </div>
                  <div className="d-flex gap-2 mt-2 mt-md-0">
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
                    <Button variant="outline-light" size="sm" onClick={openEditProjectModal}>
                      <Edit3 size={14} className="me-1" />
                      Edit Project
                    </Button>
                  </div>
                </div>

                {/* 3-Tab Navigation */}
                <Nav
                  variant="tabs"
                  className="mb-3"
                  activeKey={activeTab}
                  onSelect={(k) => setActiveTab(k)}
                >
                  <Nav.Item>
                    <Nav.Link eventKey="overview">Project Overview</Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="timeline">
                      Incident Evidence Timeline ({activeProject.evidence_count})
                    </Nav.Link>
                  </Nav.Item>
                  <Nav.Item>
                    <Nav.Link eventKey="reports">
                      Incident Report Generation ({activeProject.key_evidence_count} Key)
                    </Nav.Link>
                  </Nav.Item>
                </Nav>

                {/* TAB 1: PROJECT OVERVIEW */}
                {activeTab === 'overview' && (
                  <div className="d-flex flex-column gap-3">
                    <Card className="soc-card">
                      <Card.Header className="soc-card-header d-flex justify-content-between align-items-center">
                        <span>Incident Overview</span>
                        <Button variant="outline-light" size="sm" onClick={openEditProjectModal}>
                          Edit Overview
                        </Button>
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
                          <div className="text-secondary small mb-1">Summary of Incident</div>
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

                    {/* External Research Links & Summaries (Every item individually removable) */}
                    <Card className="soc-card">
                      <Card.Header className="soc-card-header">
                        External Research &amp; Threat Intelligence Links
                      </Card.Header>
                      <Card.Body>
                        <ul className="bullet-list mb-3">
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
                                <Button
                                  variant="outline-secondary"
                                  size="sm"
                                  title="Remove external research item"
                                  onClick={handleClearLegacyInlineResearch}
                                >
                                  <Trash2 size={13} />
                                </Button>
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
                                    <div className="text-secondary" style={{ fontSize: '0.72rem' }}>
                                      Added by {r.analyst_name}
                                    </div>
                                  )}
                                </div>
                                <Button
                                  variant="outline-secondary"
                                  size="sm"
                                  title="Remove external research item"
                                  onClick={() => handleDeleteExternalResearch(r.id)}
                                >
                                  <Trash2 size={13} />
                                </Button>
                              </div>
                            </li>
                          ))}

                          {!activeProject.external_research_link &&
                            !activeProject.external_research_summary &&
                            (!activeProject.external_research_items ||
                              activeProject.external_research_items.length === 0) && (
                              <li className="text-secondary small">No external research recorded.</li>
                            )}
                        </ul>

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
                      </Card.Body>
                    </Card>
                  </div>
                )}

                {/* TAB 2: INCIDENT EVIDENCE TIMELINE */}
                {activeTab === 'timeline' && (
                  <Card className="soc-card">
                    <Card.Header className="soc-card-header py-3">
                      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
                        <span>Chronological Evidence Timeline</span>
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
                              <th style={{ width: '90px' }}>Key</th>
                              <th style={{ width: '185px' }}>Timestamp (UTC)</th>
                              <th style={{ width: '130px' }}>Type / Analyst</th>
                              <th style={{ width: '175px' }}>Asset &amp; User</th>
                              <th>Analyst Notes, Indicators &amp; Commands</th>
                              <th style={{ width: '180px' }}>MITRE ATT&amp;CK</th>
                              <th style={{ width: '150px' }}>Screenshots</th>
                              <th style={{ width: '150px' }}>Links</th>
                              <th style={{ width: '100px' }} className="text-end">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredTimeline.map((item) => (
                              <tr
                                key={item.id}
                                className={item.is_key_evidence ? 'timeline-row-key' : ''}
                              >
                                <td>
                                  <Button
                                    variant={item.is_key_evidence ? 'outline-light' : 'outline-secondary'}
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
                                    <span className={item.is_key_evidence ? 'text-lb-lime' : ''}>
                                      {item.is_key_evidence ? 'Key' : 'Flag'}
                                    </span>
                                  </Button>
                                </td>

                                <td className="mono-text small">
                                  <div className="text-white">{formatUtcTimestamp(item.timestamp)}</div>
                                  {item.evidence_type === 'SEARCH' && item.end_timestamp && (
                                    <div className="text-secondary mt-1">
                                      to {formatUtcTimestamp(item.end_timestamp)}
                                    </div>
                                  )}
                                </td>

                                <td className="small">
                                  <div className="fw-semibold text-lb-cyan">
                                    {item.evidence_type === 'ATOMIC' ? 'Atomic Event' : 'Search Result'}
                                  </div>
                                  <div className="text-secondary">{item.analyst_name || '—'}</div>
                                </td>

                                <td className="mono-text small">
                                  <div>{defangText(item.affected_asset) || '—'}</div>
                                  <div className="text-secondary mt-1">
                                    {item.affected_user || '—'}
                                    {item.user_created_by_attacker && ' (Attacker-Created)'}
                                  </div>
                                </td>

                                <td className="small">
                                  {item.summary && <div className="mb-1">{item.summary}</div>}
                                  {item.notes && (
                                    <div className="text-secondary mb-1">Notes: {item.notes}</div>
                                  )}
                                  {item.malicious_hosts_ips && (
                                    <div className="mono-text text-lb-cyan mb-1">
                                      Indicators: {defangText(item.malicious_hosts_ips)}
                                    </div>
                                  )}
                                  {item.commands_run && (
                                    <pre className="cmd-pre mt-1">{defangText(item.commands_run)}</pre>
                                  )}
                                </td>

                                <td className="small">
                                  {item.mitre_tactic || item.mitre_technique ? (
                                    <div>
                                      {item.mitre_tactic && (
                                        <div className="fw-semibold">{item.mitre_tactic}</div>
                                      )}
                                      {item.mitre_technique && (
                                        <div className="text-secondary mono-text">
                                          {item.mitre_technique}
                                        </div>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-secondary">—</span>
                                  )}
                                </td>

                                <td>
                                  {item.screenshots && item.screenshots.length > 0 ? (
                                    <div className="d-flex flex-wrap gap-2">
                                      {item.screenshots.map((shot) => (
                                        <div
                                          key={shot.id}
                                          className="position-relative d-inline-block"
                                        >
                                          <img
                                            src={shot.image_url}
                                            alt={shot.caption || shot.filename}
                                            title={shot.caption || shot.filename}
                                            className="screenshot-thumb"
                                            onClick={() => setPreviewScreenshot(shot)}
                                          />
                                          <button
                                            type="button"
                                            title="Delete screenshot"
                                            onClick={() => handleDeleteScreenshot(shot.id)}
                                            className="btn btn-sm btn-dark position-absolute top-0 end-0 p-0 d-flex align-items-center justify-content-center border-secondary"
                                            style={{ width: '20px', height: '20px', lineHeight: 1 }}
                                          >
                                            <X size={12} />
                                          </button>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-secondary small">—</span>
                                  )}
                                </td>

                                {/* Analyst links to logs & searches are NOT defanged */}
                                <td className="small">
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

                                <td className="text-end">
                                  <div className="d-flex justify-content-end gap-1">
                                    <Button
                                      variant="outline-light"
                                      size="sm"
                                      onClick={() => openEditEvidenceModal(item)}
                                    >
                                      <Edit3 size={13} />
                                    </Button>
                                    <Button
                                      variant="outline-secondary"
                                      size="sm"
                                      onClick={() => handleDeleteEvidence(item.id)}
                                    >
                                      <Trash2 size={13} />
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </Table>
                      )}
                    </Card.Body>
                  </Card>
                )}

                {/* TAB 3: INCIDENT REPORT GENERATION */}
                {activeTab === 'reports' && (
                  <div className="d-flex flex-column gap-3">
                    <Row className="g-3">
                      <Col md={6}>
                        <Card className="soc-card h-100">
                          <Card.Header className="soc-card-header">
                            Report 1: Evidence Timeline Report (CSV)
                          </Card.Header>
                          <Card.Body className="d-flex flex-column justify-content-between">
                            <p className="small text-secondary mb-3">
                              Exports all {activeProject.evidence_count} evidence items in chronological
                              order as a CSV file, with defanged assets/indicators and MITRE tactics and
                              techniques.
                            </p>
                            <div>
                              <Button
                                as="a"
                                href={api.getCsvReportUrl(activeProject.id)}
                                className="btn-lb-primary"
                                size="sm"
                              >
                                <FileSpreadsheet size={15} className="me-2" />
                                Download Timeline CSV
                              </Button>
                            </div>
                          </Card.Body>
                        </Card>
                      </Col>

                      <Col md={6}>
                        <Card className="soc-card h-100">
                          <Card.Header className="soc-card-header">
                            Report 2: Key Evidence Formatted Document (.ODT / .MD)
                          </Card.Header>
                          <Card.Body className="d-flex flex-column justify-content-between">
                            <p className="small text-secondary mb-3">
                              Exports only the {activeProject.key_evidence_count} Key Evidence items in
                              chronological order followed by summary tables for Key Assets Affected, Key
                              Malicious Indicators, and MITRE Tactics &amp; Techniques.
                            </p>
                            <div className="d-flex flex-wrap gap-2">
                              <Button
                                as="a"
                                href={api.getOdtReportUrl(activeProject.id)}
                                className="btn-lb-primary"
                                size="sm"
                              >
                                <FileText size={15} className="me-2" />
                                Download OpenDocument (.ODT)
                              </Button>
                              <Button
                                as="a"
                                href={api.getMdZipReportUrl(activeProject.id)}
                                className="btn-lb-cyan"
                                size="sm"
                              >
                                Download Markdown + Screenshots Folder (.ZIP)
                              </Button>
                              <Button
                                as="a"
                                href={api.getMdReportUrl(activeProject.id)}
                                variant="outline-light"
                                size="sm"
                              >
                                Download .MD File
                              </Button>
                            </div>
                          </Card.Body>
                        </Card>
                      </Col>
                    </Row>

                    {/* Structured Key Evidence Report Preview */}
                    <Card className="soc-card">
                      <Card.Header className="soc-card-header">
                        Report 2 Structure Preview
                      </Card.Header>
                      <Card.Body className="d-flex flex-column gap-4">
                        {/* 1. TITLE & 2. Summary of Incident */}
                        <div className="p-3 soc-subbox">
                          <h4 className="text-white fw-bold mb-2">
                            {activeProject.title || `Incident #${activeProject.id}`}
                          </h4>
                          <div className="text-lb-cyan small fw-semibold mb-1">
                            Summary of Incident
                          </div>
                          <div>{activeProject.summary || 'No summary of incident recorded.'}</div>
                        </div>

                        {/* 3. Key Evidence Timeline (starts directly with TIMESTAMP, ASSET, USER:) */}
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

                        {/* 4. Summary Tables at the Bottom */}
                        <div>
                          <h6 className="text-lb-cyan fw-semibold mb-3">
                            Summary Tables (Bottom of Report)
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
            projects sidebar.
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

      {/* Modal: Create / Edit Project Overview */}
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
              {editingProject ? 'Edit Project Overview' : 'Create Incident Project'}
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
                    onChange={(e) => setProjectForm({ ...projectForm, customer_id: e.target.value })}
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
                    onChange={(e) => setProjectForm({ ...projectForm, ticket_link: e.target.value })}
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">Summary of Incident</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    value={projectForm.summary}
                    onChange={(e) => setProjectForm({ ...projectForm, summary: e.target.value })}
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
                  <Form.Label className="small">Key Malicious Indicators (one per line)</Form.Label>
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
                      <Form.Label className="small">Initial External Research Link (Optional)</Form.Label>
                      <Form.Control
                        type="text"
                        value={projectForm.external_research_link}
                        onChange={(e) =>
                          setProjectForm({ ...projectForm, external_research_link: e.target.value })
                        }
                      />
                    </Form.Group>
                  </Col>
                  <Col md={7}>
                    <Form.Group>
                      <Form.Label className="small">Initial External Research Summary (Optional)</Form.Label>
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
            <Button className="btn-lb-primary" type="submit">
              Save Project
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
                    onChange={(e) => setEvidenceForm({ ...evidenceForm, summary: e.target.value })}
                  />
                </Form.Group>
              </Col>

              <Col md={12}>
                <Form.Group>
                  <Form.Label className="small">Malicious Hosts / IPs / Domains Involved</Form.Label>
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
                  <Form.Label className="small">MITRE Tactic (Optional)</Form.Label>
                  <Form.Control
                    type="text"
                    placeholder="e.g. Credential Access (TA0006)"
                    value={evidenceForm.mitre_tactic}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, mitre_tactic: e.target.value })
                    }
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group>
                  <Form.Label className="small">MITRE Technique (Optional)</Form.Label>
                  <Form.Control
                    type="text"
                    placeholder="e.g. T1003.001 - LSASS Memory"
                    value={evidenceForm.mitre_technique}
                    onChange={(e) =>
                      setEvidenceForm({ ...evidenceForm, mitre_technique: e.target.value })
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
                          setEvidenceForm({ ...evidenceForm, search_result_link: e.target.value })
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
                          setEvidenceForm({ ...evidenceForm, search_query_link: e.target.value })
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

      {/* Modal: Screenshot Preview with Delete Button */}
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
          {previewScreenshot && (
            <Button
              variant="outline-danger"
              size="sm"
              onClick={() => handleDeleteScreenshot(previewScreenshot.id)}
            >
              <Trash2 size={14} className="me-1" />
              Delete Screenshot
            </Button>
          )}
          <Button variant="outline-secondary" size="sm" onClick={() => setPreviewScreenshot(null)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}
