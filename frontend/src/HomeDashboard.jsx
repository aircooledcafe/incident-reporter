import React, { useState } from 'react';
import { Card, Row, Col, Button, Badge, Form, Spinner } from 'react-bootstrap';
import {
  ExternalLink,
  Lock,
  Plus,
  FolderOpen,
  ClipboardList,
  ArrowUpDown,
  Sparkles,
} from 'lucide-react';

const STATUS_LABELS = {
  OPEN: 'Open / Triage',
  INVESTIGATING: 'Investigating',
  CONTAINED: 'Contained',
  ARCHIVED: 'Archived / Closed',
};

function formatUtcShort(isoString) {
  if (!isoString) return 'N/A';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
}

export default function HomeDashboard({
  projects,
  loading,
  canEditRole,
  canSeedDemo,
  onOpenInvestigation,
  onOpenNewProject,
  onSeedDemoScenario,
  demoScenarios,
}) {
  // Filter toggle: 'open' (default) | 'all' | 'archived' | 'locked'
  const [viewFilter, setViewFilter] = useState('open');
  // Sort order: 'chrono_desc' | 'chrono_asc' | 'customer_asc' | 'customer_desc'
  const [sortOrder, setSortOrder] = useState('chrono_desc');
  const [searchQuery, setSearchQuery] = useState('');

  const openItems = projects.filter((p) => p.status !== 'ARCHIVED' && !p.is_locked);
  const archivedItems = projects.filter((p) => p.status === 'ARCHIVED');
  const lockedItems = projects.filter((p) => Boolean(p.is_locked));

  const bucketItems = (() => {
    switch (viewFilter) {
      case 'all':
        return projects;
      case 'archived':
        return archivedItems;
      case 'locked':
        return lockedItems;
      case 'open':
      default:
        return openItems;
    }
  })();

  const searchedItems = bucketItems.filter((p) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.trim().toLowerCase();
    const haystack = [
      p.title,
      p.customer_name,
      p.customer_id,
      p.ticket_id,
      p.summary,
      p.action_plan,
      p.lead_analyst,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return haystack.includes(q);
  });

  const sortedItems = [...searchedItems].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    const custA = (a.customer_name || '').trim().toLowerCase();
    const custB = (b.customer_name || '').trim().toLowerCase();

    if (sortOrder === 'chrono_asc') {
      return timeA - timeB;
    }
    if (sortOrder === 'customer_asc') {
      if (!custA && custB) return 1;
      if (custA && !custB) return -1;
      const cmp = custA.localeCompare(custB);
      return cmp !== 0 ? cmp : timeB - timeA;
    }
    if (sortOrder === 'customer_desc') {
      if (!custA && custB) return 1;
      if (custA && !custB) return -1;
      const cmp = custB.localeCompare(custA);
      return cmp !== 0 ? cmp : timeB - timeA;
    }
    return timeB - timeA;
  });

  const filterButtons = [
    { key: 'open', label: 'Open', count: openItems.length },
    { key: 'all', label: 'All', count: projects.length },
    { key: 'archived', label: 'Archived', count: archivedItems.length },
    { key: 'locked', label: 'Locked', count: lockedItems.length },
  ];

  return (
    <div className="d-flex flex-column gap-3">
      {/* Top Controls Bar */}
      <Card className="soc-card">
        <Card.Header className="soc-card-header py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <div>
              <h5 className="mb-1 text-white fw-semibold">
                SOC Incident Investigations Overview
              </h5>
              <div className="small text-secondary fw-normal">
                Review active incident investigations, ticket links, customer details, incident summaries, and analyst action plans.
              </div>
            </div>

            {canEditRole && (
              <div className="d-flex flex-wrap gap-2">
                <Button className="btn-lb-primary" size="sm" onClick={onOpenNewProject}>
                  <Plus size={15} className="me-1" />
                  New Investigation
                </Button>
              </div>
            )}
          </div>
        </Card.Header>

        <Card.Body className="py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            {/* Toggles: Open | All | Archived | Locked */}
            <div className="d-flex flex-wrap align-items-center gap-2" role="group" aria-label="Investigation status filters">
              {filterButtons.map((btn) => {
                const active = viewFilter === btn.key;
                return (
                  <Button
                    key={btn.key}
                    size="sm"
                    className={active ? 'btn-lb-primary' : ''}
                    variant={active ? undefined : 'outline-secondary'}
                    onClick={() => setViewFilter(btn.key)}
                  >
                    <span>{btn.label}</span>
                    <Badge
                      bg={active ? 'light' : 'dark'}
                      text={active ? 'dark' : 'light'}
                      className="ms-2 border border-secondary"
                    >
                      {btn.count}
                    </Badge>
                  </Button>
                );
              })}
            </div>

            {/* Ordering & Search Controls */}
            <div className="d-flex flex-wrap align-items-center gap-2">
              <div className="d-flex align-items-center gap-2">
                <ArrowUpDown size={15} className="text-lb-cyan" />
                <Form.Select
                  size="sm"
                  aria-label="Order investigations"
                  style={{ width: '245px' }}
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value)}
                >
                  <option value="chrono_desc">Order: Chronological (Newest First)</option>
                  <option value="chrono_asc">Order: Chronological (Oldest First)</option>
                  <option value="customer_asc">Order: Customer Name (A &rarr; Z)</option>
                  <option value="customer_desc">Order: Customer Name (Z &rarr; A)</option>
                </Form.Select>
              </div>

              <Form.Control
                size="sm"
                type="text"
                placeholder="Search customer, ticket, summary..."
                style={{ width: '230px' }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </Card.Body>
      </Card>

      {/* Investigation Cards */}
      {loading && projects.length === 0 ? (
        <div className="text-center py-5">
          <Spinner animation="border" variant="info" />
        </div>
      ) : sortedItems.length === 0 ? (
        <Card className="soc-card text-center py-5">
          <Card.Body>
            <h6 className="text-white mb-2">
              No {viewFilter === 'all' ? '' : viewFilter} investigations match the current filter.
            </h6>
            <p className="text-secondary small mb-3">
              Switch filter toggles above{canEditRole ? ' or start a new incident investigation.' : '.'}
            </p>
            <div className="d-flex flex-wrap justify-content-center gap-2">
              {viewFilter !== 'all' && projects.length > 0 && (
                <Button variant="outline-light" size="sm" onClick={() => setViewFilter('all')}>
                  View All Investigations ({projects.length})
                </Button>
              )}
              {canEditRole && (
                <Button className="btn-lb-primary" size="sm" onClick={onOpenNewProject}>
                  <Plus size={14} className="me-1" />
                  Create New Investigation
                </Button>
              )}
              {canSeedDemo && demoScenarios && demoScenarios.length > 0 && (
                <Button
                  className="btn-lb-cyan"
                  size="sm"
                  onClick={() => onSeedDemoScenario('all')}
                >
                  <Sparkles size={14} className="me-1" />
                  Load All 4 Demo Incidents
                </Button>
              )}
            </div>
          </Card.Body>
        </Card>
      ) : (
        <div className="d-flex flex-column gap-3">
          {sortedItems.map((project) => (
            <div key={project.id} className="home-investigation-card p-3">
              {/* Top Row: Title, Badges, Open Investigation Button */}
              <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 pb-2 mb-3 border-bottom border-secondary">
                <div>
                  <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                    <button
                      type="button"
                      onClick={() => onOpenInvestigation(project.id)}
                      className="btn btn-link p-0 text-start text-white fw-semibold text-decoration-none fs-5"
                    >
                      {project.title || `Incident #${project.id}`}
                    </button>

                    <Badge
                      bg={project.status === 'ARCHIVED' ? 'secondary' : 'dark'}
                      className="border border-secondary text-lb-cyan fw-normal"
                    >
                      {STATUS_LABELS[project.status] || project.status}
                    </Badge>

                    {project.is_locked && (
                      <Badge bg="warning" text="dark" className="d-inline-flex align-items-center gap-1">
                        <Lock size={11} />
                        Locked
                      </Badge>
                    )}
                  </div>

                  <div className="small text-secondary d-flex flex-wrap align-items-center gap-3">
                    <span>
                      Customer:{' '}
                      <strong className="text-light">
                        {project.customer_name || 'Unspecified Customer'}
                      </strong>
                      {project.customer_id ? ` (${project.customer_id})` : ''}
                    </span>

                    <span>
                      Ticket:{' '}
                      {project.ticket_link ? (
                        <a
                          href={project.ticket_link}
                          target="_blank"
                          rel="noreferrer"
                          className="text-lb-cyan mono-text text-decoration-none"
                        >
                          {project.ticket_id || project.ticket_link} <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span className="mono-text text-light">{project.ticket_id || 'N/A'}</span>
                      )}
                    </span>

                    <span>Lead: {project.lead_analyst || 'Unassigned'}</span>
                    <span className="mono-text">Created: {formatUtcShort(project.created_at)}</span>
                    <span>
                      {project.evidence_count} events ({project.key_evidence_count} key)
                    </span>
                  </div>
                </div>

                <Button
                  className="btn-lb-primary"
                  size="sm"
                  onClick={() => onOpenInvestigation(project.id)}
                >
                  <FolderOpen size={14} className="me-1" />
                  Open Investigation
                </Button>
              </div>

              {/* Related Escalated Incidents Strip (if any) */}
              {project.related_incidents && project.related_incidents.length > 0 && (
                <div className="mb-3 d-flex flex-wrap align-items-center gap-2 small">
                  <span className="text-secondary">Related Escalations:</span>
                  {project.related_incidents.map((rel) => (
                    <a
                      key={rel.id}
                      href={rel.link}
                      target="_blank"
                      rel="noreferrer"
                      className="badge bg-dark border border-secondary text-lb-cyan text-decoration-none fw-normal py-1 px-2"
                    >
                      {rel.title} <ExternalLink size={11} className="ms-1" />
                    </a>
                  ))}
                </div>
              )}

              {/* Summary & Action Plan Columns */}
              <Row className="g-3">
                <Col lg={6}>
                  <div className="p-3 soc-subbox h-100">
                    <div className="small fw-semibold text-lb-cyan mb-1">Incident Summary</div>
                    <div className="small pre-wrap-text">
                      {project.summary || (
                        <span className="text-secondary">No incident summary recorded yet.</span>
                      )}
                    </div>
                  </div>
                </Col>
                <Col lg={6}>
                  <div className="p-3 soc-subbox h-100">
                    <div className="small fw-semibold text-lb-lime mb-1 d-flex align-items-center gap-1">
                      <ClipboardList size={14} />
                      <span>Action Plan &amp; Next Steps</span>
                    </div>
                    <div className="small pre-wrap-text">
                      {project.action_plan ? (
                        project.action_plan
                      ) : (
                        <span className="text-secondary">
                          No action plan recorded yet. Open investigation to add next steps or customer requests.
                        </span>
                      )}
                    </div>
                  </div>
                </Col>
              </Row>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
