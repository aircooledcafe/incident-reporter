import React from 'react';
import { Modal, Row, Col, Badge, Button } from 'react-bootstrap';
import { Star, ExternalLink, Edit3, Trash2, Image as ImageIcon } from 'lucide-react';
import { splitMitreValues } from './mitreData';

function formatUtcTimestamp(isoString) {
  if (!isoString) return 'N/A';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return isoString;
  return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
}

export default function EvidenceDetailModal({
  item,
  show,
  onHide,
  defangText,
  canModifyActiveProject,
  onToggleKey,
  onEdit,
  onDelete,
  onPreviewScreenshot,
  onDeleteScreenshot,
}) {
  if (!item) return null;

  const tactics = splitMitreValues(item.mitre_tactic);
  const techniques = splitMitreValues(item.mitre_technique);
  const screenshots = item.screenshots || [];
  const hasAnyLinks = Boolean(
    item.related_log_link || item.search_result_link || item.search_query_link,
  );

  return (
    <Modal show={show} onHide={onHide} size="lg" transition={false} centered>
      <Modal.Header closeButton className="bg-dark border-secondary">
        <div className="d-flex flex-wrap align-items-center gap-2">
          <Modal.Title className="fs-6 mb-0 text-white">
            Evidence Item Details
          </Modal.Title>
          <Badge bg="dark" className="border border-info text-lb-cyan fw-normal">
            {item.evidence_type === 'ATOMIC'
              ? 'Atomic Event (IDS / Log Event)'
              : 'Search Result (Activity Pattern Over Time)'}
          </Badge>
          {item.is_key_evidence && (
            <Badge bg="dark" className="border border-success text-lb-lime d-inline-flex align-items-center gap-1">
              <Star size={12} fill="#9CEF69" color="#9CEF69" />
              Key Evidence
            </Badge>
          )}
        </div>
      </Modal.Header>

      <Modal.Body className="bg-dark text-light d-flex flex-column gap-3">
        {/* Top Metadata Grid */}
        <div className="p-3 soc-subbox">
          <Row className="g-3">
            <Col md={item.evidence_type === 'SEARCH' ? 4 : 6}>
              <div className="text-secondary small">
                {item.evidence_type === 'SEARCH' ? 'Start Timestamp (UTC)' : 'Timestamp (UTC)'}
              </div>
              <div className="mono-text fw-semibold text-white">
                {formatUtcTimestamp(item.timestamp)}
              </div>
            </Col>

            {item.evidence_type === 'SEARCH' && (
              <Col md={4}>
                <div className="text-secondary small">End Timestamp (UTC)</div>
                <div className="mono-text fw-semibold text-white">
                  {item.end_timestamp ? formatUtcTimestamp(item.end_timestamp) : 'N/A'}
                </div>
              </Col>
            )}

            <Col md={item.evidence_type === 'SEARCH' ? 4 : 6}>
              <div className="text-secondary small">Analyst</div>
              <div className="fw-semibold text-white">{item.analyst_name || '—'}</div>
            </Col>

            <Col md={6}>
              <div className="text-secondary small">Affected Asset (Defanged)</div>
              <div className="mono-text text-white">
                {defangText(item.affected_asset) || '—'}
              </div>
            </Col>

            <Col md={6}>
              <div className="text-secondary small">Affected User</div>
              <div className="mono-text text-white d-flex flex-wrap align-items-center gap-2">
                <span>{item.affected_user || '—'}</span>
                {item.user_created_by_attacker && (
                  <Badge bg="danger" style={{ fontSize: '0.68rem' }}>
                    Created by Attacker
                  </Badge>
                )}
              </div>
            </Col>
          </Row>
        </div>

        {/* Summary & Freeform Analyst Notes */}
        <Row className="g-3">
          <Col md={12}>
            <div className="p-3 soc-subbox">
              <div className="small fw-semibold text-lb-cyan mb-1">Summary of Evidence</div>
              <div className="pre-wrap-text small">
                {item.summary || <span className="text-secondary">No summary recorded.</span>}
              </div>
            </div>
          </Col>

          <Col md={12}>
            <div className="p-3 soc-subbox">
              <div className="small fw-semibold text-lb-cyan mb-1">Analyst Notes</div>
              <div className="pre-wrap-text small">
                {item.notes || <span className="text-secondary">No freeform notes recorded.</span>}
              </div>
            </div>
          </Col>
        </Row>

        {/* Malicious Indicators & Commands Run */}
        <Row className="g-3">
          <Col md={12}>
            <div className="p-3 soc-subbox">
              <div className="small fw-semibold text-lb-cyan mb-1">
                Malicious Hosts / IPs / Domains Involved (Defanged)
              </div>
              <div className="mono-text pre-wrap-text small">
                {item.malicious_hosts_ips ? (
                  defangText(item.malicious_hosts_ips)
                ) : (
                  <span className="text-secondary">None recorded.</span>
                )}
              </div>
            </div>
          </Col>

          <Col md={12}>
            <div className="p-3 soc-subbox">
              <div className="small fw-semibold text-lb-cyan mb-1">Commands Run (Defanged)</div>
              {item.commands_run ? (
                <pre className="cmd-pre mt-1">{defangText(item.commands_run)}</pre>
              ) : (
                <div className="small text-secondary">None recorded.</div>
              )}
            </div>
          </Col>
        </Row>

        {/* MITRE ATT&CK Tactics & Techniques */}
        <div className="p-3 soc-subbox">
          <div className="small fw-semibold text-lb-cyan mb-2">
            MITRE ATT&amp;CK Tactics &amp; Techniques
          </div>
          {tactics.length === 0 && techniques.length === 0 ? (
            <div className="small text-secondary">No MITRE ATT&amp;CK mappings recorded.</div>
          ) : (
            <Row className="g-2">
              <Col md={6}>
                <div className="text-secondary" style={{ fontSize: '0.75rem' }}>
                  Tactics
                </div>
                {tactics.length === 0 ? (
                  <div className="small text-secondary">—</div>
                ) : (
                  <div className="d-flex flex-wrap gap-1 mt-1">
                    {tactics.map((tac, idx) => (
                      <Badge
                        key={`tac-${idx}`}
                        bg="dark"
                        className="border border-info text-lb-cyan fw-normal"
                      >
                        {tac}
                      </Badge>
                    ))}
                  </div>
                )}
              </Col>
              <Col md={6}>
                <div className="text-secondary" style={{ fontSize: '0.75rem' }}>
                  Techniques
                </div>
                {techniques.length === 0 ? (
                  <div className="small text-secondary">—</div>
                ) : (
                  <div className="d-flex flex-wrap gap-1 mt-1">
                    {techniques.map((tech, idx) => (
                      <Badge
                        key={`tech-${idx}`}
                        bg="dark"
                        className="border border-secondary text-light mono-text fw-normal"
                      >
                        {tech}
                      </Badge>
                    ))}
                  </div>
                )}
              </Col>
            </Row>
          )}
        </div>

        {/* Evidence Links (Not Defanged) */}
        <div className="p-3 soc-subbox">
          <div className="small fw-semibold text-lb-cyan mb-2">Evidence &amp; SIEM Links</div>
          {!hasAnyLinks ? (
            <div className="small text-secondary">No links attached.</div>
          ) : (
            <div className="d-flex flex-column gap-1 small">
              {item.related_log_link && (
                <div>
                  <span className="text-secondary me-2">Related Log / IDS Link:</span>
                  <a
                    href={item.related_log_link}
                    target="_blank"
                    rel="noreferrer"
                    className="text-lb-cyan mono-text text-decoration-none"
                  >
                    {item.related_log_link} <ExternalLink size={12} />
                  </a>
                </div>
              )}
              {item.search_result_link && (
                <div>
                  <span className="text-secondary me-2">Search Result Link:</span>
                  <a
                    href={item.search_result_link}
                    target="_blank"
                    rel="noreferrer"
                    className="text-lb-cyan mono-text text-decoration-none"
                  >
                    {item.search_result_link} <ExternalLink size={12} />
                  </a>
                </div>
              )}
              {item.search_query_link && (
                <div>
                  <span className="text-secondary me-2">Search Query Link:</span>
                  <a
                    href={item.search_query_link}
                    target="_blank"
                    rel="noreferrer"
                    className="text-lb-cyan mono-text text-decoration-none"
                  >
                    {item.search_query_link} <ExternalLink size={12} />
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Attached Screenshots */}
        <div className="p-3 soc-subbox">
          <div className="small fw-semibold text-lb-cyan mb-2 d-flex align-items-center gap-1">
            <ImageIcon size={14} />
            <span>Screenshots ({screenshots.length})</span>
          </div>
          {screenshots.length === 0 ? (
            <div className="small text-secondary">No screenshots attached to this evidence item.</div>
          ) : (
            <div className="d-flex flex-wrap gap-3">
              {screenshots.map((shot) => (
                <div
                  key={shot.id}
                  className="p-2 rounded border border-secondary bg-dark d-flex flex-column gap-2"
                  style={{ maxWidth: '220px' }}
                >
                  <img
                    src={shot.image_url}
                    alt={shot.caption || shot.filename}
                    title="Click to enlarge screenshot"
                    className="img-fluid rounded border border-secondary"
                    style={{ maxHeight: '130px', objectFit: 'cover', cursor: 'pointer' }}
                    onClick={() => onPreviewScreenshot(shot)}
                  />
                  <div className="small text-truncate" title={shot.caption || shot.filename}>
                    {shot.caption || shot.filename}
                  </div>
                  {canModifyActiveProject && (
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => onDeleteScreenshot(shot.id)}
                    >
                      <Trash2 size={12} className="me-1" />
                      Remove
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Audit Timestamps */}
        <div className="d-flex flex-wrap justify-content-between text-secondary" style={{ fontSize: '0.74rem' }}>
          <span>Created: {formatUtcTimestamp(item.created_at)}</span>
          <span>Last Updated: {formatUtcTimestamp(item.updated_at)}</span>
        </div>
      </Modal.Body>

      <Modal.Footer className="bg-dark border-secondary justify-content-between">
        <div className="d-flex flex-wrap gap-2">
          {canModifyActiveProject && (
            <>
              <Button
                variant={item.is_key_evidence ? 'outline-light' : 'outline-secondary'}
                size="sm"
                onClick={() => onToggleKey(item.id)}
              >
                <Star
                  size={14}
                  fill={item.is_key_evidence ? '#9CEF69' : 'none'}
                  color={item.is_key_evidence ? '#9CEF69' : '#94a3b8'}
                  className="me-1"
                />
                <span className={item.is_key_evidence ? 'text-lb-lime' : ''}>
                  {item.is_key_evidence ? 'Unflag Key Evidence' : 'Flag as Key Evidence'}
                </span>
              </Button>
              <Button
                className="btn-lb-primary"
                size="sm"
                onClick={() => {
                  onHide();
                  onEdit(item);
                }}
              >
                <Edit3 size={14} className="me-1" />
                Edit Evidence
              </Button>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => {
                  onHide();
                  onDelete(item.id);
                }}
              >
                <Trash2 size={14} className="me-1" />
                Delete
              </Button>
            </>
          )}
        </div>

        <Button variant="outline-secondary" size="sm" onClick={onHide}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
