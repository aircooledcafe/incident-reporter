import React, { useState } from 'react';
import { Card, Row, Col, Button, Badge, Form, Spinner } from 'react-bootstrap';
import {
  ExternalLink,
  Lock,
  Plus,
  ClipboardList,
  ArrowUpDown,
  Sparkles,
} from 'lucide-react';
import { safeHref } from './api';

const STATUS_LABELS = {
  OPEN: 'Triage',
  INVESTIGATING: 'Investigating',
  AWAITING_CUSTOMER: 'Awaiting Customer',
  CONTAINED: 'Contained',
  ARCHIVED: 'Closed',
};

const FILTER_LABELS = {
  open: 'open',
  all: '',
  OPEN: 'triage',
  INVESTIGATING: 'investigating',
  AWAITING_CUSTOMER: 'awaiting-customer',
  CONTAINED: 'contained',
  archived: 'closed',
  locked: 'locked',
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
  // Filter toggle: 'open' (default) | 'all' | status | 'archived' | 'locked'
  const [viewFilter, setViewFilter] = useState('open');
  // Sort order: 'chrono_desc' | 'chrono_asc' | 'customer_asc' | 'customer_desc'
  const [sortOrder, setSortOrder] = useState('chrono_desc');
  const [searchQuery, setSearchQuery] = useState('');

  const openItems = projects.filter((p) => p.status !== 'ARCHIVED' && !p.is_locked);
  const triageItems = projects.filter((p) => p.status === 'OPEN');
  const investigatingItems = projects.filter((p) => p.status === 'INVESTIGATING');
  const awaitingCustomerItems = projects.filter((p) => p.status === 'AWAITING_CUSTOMER');
  const containedItems = projects.filter((p) => p.status === 'CONTAINED');
  const archivedItems = projects.filter((p) => p.status === 'ARCHIVED');
  const lockedItems = projects.filter((p) => Boolean(p.is_locked));

  const bucketItems = (() => {
    switch (viewFilter) {
      case 'all':
        return projects;
      case 'OPEN':
        return triageItems;
      case 'INVESTIGATING':
        return investigatingItems;
      case 'AWAITING_CUSTOMER':
        return awaitingCustomerItems;
      case 'CONTAINED':
        return containedItems;
      case 'archived':
      case 'ARCHIVED':
      case 'closed':
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

  return (
    <div className="d-flex flex-column gap-3">
      {/* Top Controls Bar */}
      <Card className="soc-card">
        <Card.Header className="soc-card-header py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <div>
              <h5 className="mb-1 text-white fw-semibold">
                SOC Investigation Overview
              </h5>
              <div className="small text-secondary fw-normal">
                Review active investigations, ticket links, customer details, investigation summaries, and analyst action plans.
              </div>
            </div>
          </div>
        </Card.Header>

        <Card.Body className="py-3">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            {/* Status Filter Dropdown */}
            <div className="d-flex align-items-center gap-2">
              <span className="small text-secondary fw-semibold text-nowrap">Filter:</span>
              <Form.Select
                size="sm"
                value={viewFilter}
                onChange={(e) => setViewFilter(e.target.value)}
                className="bg-dark text-light border-secondary"
                style={{ width: '220px' }}
                aria-label="Filter investigations by status"
              >
                <option value="open">Open ({openItems.length})</option>
                <option value="all">All ({projects.length})</option>
                <option value="OPEN">Triage ({triageItems.length})</option>
                <option value="INVESTIGATING">Investigating ({investigatingItems.length})</option>
                <option value="AWAITING_CUSTOMER">Awaiting Customer ({awaitingCustomerItems.length})</option>
                <option value="CONTAINED">Contained ({containedItems.length})</option>
                <option value="archived">Closed ({archivedItems.length})</option>
                <option value="locked">Locked ({lockedItems.length})</option>
              </Form.Select>
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
              No {FILTER_LABELS[viewFilter] ? `${FILTER_LABELS[viewFilter]} ` : ''}investigations match the current filter.
            </h6>
            <p className="text-secondary small mb-3">
              Change the filter selection above{canEditRole ? ' or start a new investigation.' : '.'}
            </p>
            <div className="d-flex flex-wrap justify-content-center gap-2">
              {viewFilter !== 'all' && projects.length > 0 && (
                <Button variant="outline-light" size="sm" onClick={() => setViewFilter('all')}>
                  View All Investigations ({projects.length})
                </Button>
              )}
              {canEditRole && (
                <Button className="btn-lb-green" size="sm" onClick={onOpenNewProject}>
                  <Plus size={14} className="me-1" />
                  New Investigation
                </Button>
              )}
              {canSeedDemo && demoScenarios && demoScenarios.length > 0 && (
                <Button
                  className="btn-lb-cyan"
                  size="sm"
                  onClick={() => onSeedDemoScenario('all')}
                >
                  <Sparkles size={14} className="me-1" />
                  Load All {demoScenarios.length} Demo Investigations
                </Button>
              )}
            </div>
          </Card.Body>
        </Card>
      ) : (
        <div className="d-flex flex-column gap-3">
          {sortedItems.map((project) => (
            <div
              key={project.id}
              className="home-investigation-card p-3"
              onClick={() => onOpenInvestigation(project.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onOpenInvestigation(project.id);
                }
              }}
            >
              {/* Top Row: Title, Badges */}
              <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 pb-2 mb-3 border-bottom border-secondary">
                <div>
                  <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                    <span className="text-white fw-semibold fs-5">
                      {project.title || `Investigation ${project.investigation_id || '#' + project.id}`}
                    </span>

                    <Badge
                      bg="dark"
                      className="border border-secondary text-lb-cyan fw-normal font-monospace"
                      style={{ fontSize: '0.72rem' }}
                    >
                      {project.investigation_id || `INV${String(project.id).padStart(6, '0')}`}
                    </Badge>

                    <Badge
                      bg={project.status === 'ARCHIVED' ? 'secondary' : 'dark'}
                      className={`border ${
                        project.status === 'INVESTIGATING'
                          ? 'border-lb-lime text-lb-lime'
                          : 'border-secondary text-lb-cyan'
                      } fw-normal`}
                      style={{ fontSize: '0.72rem' }}
                    >
                      {STATUS_LABELS[project.status] || project.status}
                    </Badge>

                    {project.is_locked && (
                      <Badge bg="warning" text="dark" className="d-inline-flex align-items-center gap-1" style={{ fontSize: '0.72rem' }}>
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
                      {safeHref(project.ticket_link) ? (
                        <a
                          href={safeHref(project.ticket_link)}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
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
              </div>

              {/* Related Escalated Incidents Strip (if any) */}
              {project.related_incidents && project.related_incidents.length > 0 && (
                <div className="mb-3 d-flex flex-wrap align-items-center gap-2 small">
                  <span className="text-secondary">Related Escalations:</span>
                  {project.related_incidents.map((rel) => {
                    const relHref = safeHref(rel.link);
                    return relHref ? (
                      <a
                        key={rel.id}
                        href={relHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="badge bg-dark border border-secondary text-lb-cyan text-decoration-none fw-normal py-1 px-2"
                      >
                        {rel.title} <ExternalLink size={11} className="ms-1" />
                      </a>
                    ) : (
                      <span
                        key={rel.id}
                        className="badge bg-dark border border-secondary text-light fw-normal py-1 px-2"
                      >
                        {rel.title}
                      </span>
                    );
                  })}
                </div>
              )}

              {/* Summary & Action Plan Columns */}
              <Row className="g-3">
                <Col lg={6}>
                  <div className="p-3 soc-subbox h-100">
                    <div className="small fw-semibold text-lb-cyan mb-1">Investigation Summary</div>
                    <div className="small pre-wrap-text">
                      {project.summary || (
                        <span className="text-secondary">No investigation summary recorded yet.</span>
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
