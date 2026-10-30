import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Form, Button, Table } from 'react-bootstrap';
import {
  ClipboardList,
  ExternalLink,
  Trash2,
  Plus,
  Phone,
  Mail,
  Link2,
  UserCheck,
  Save,
} from 'lucide-react';
import { api } from './api';

export default function ProjectOverviewExtras({
  activeProject,
  canModifyActiveProject,
  currentAnalystName,
  onProjectMutated,
  onNotifySuccess,
  onApiError,
}) {
  // Action Plan inline state
  const [actionPlanDraft, setActionPlanDraft] = useState('');
  const [savingActionPlan, setSavingActionPlan] = useState(false);

  // Related Escalated Incident form state
  const [relTitle, setRelTitle] = useState('');
  const [relLink, setRelLink] = useState('');

  // Customer Contact form state
  const [contactForm, setContactForm] = useState({
    name: '',
    role_title: '',
    email: '',
    phone: '',
    notes: '',
  });

  useEffect(() => {
    setActionPlanDraft(activeProject?.action_plan || '');
  }, [activeProject?.id, activeProject?.action_plan]);

  if (!activeProject) return null;

  const isActionPlanDirty = actionPlanDraft !== (activeProject.action_plan || '');

  const handleSaveActionPlan = async (e) => {
    e.preventDefault();
    if (!canModifyActiveProject) return;
    try {
      setSavingActionPlan(true);
      await api.updateProject(activeProject.id, { action_plan: actionPlanDraft });
      await onProjectMutated(activeProject.id);
      onNotifySuccess('Action plan saved.');
    } catch (err) {
      onApiError(err, 'Failed to save action plan');
    } finally {
      setSavingActionPlan(false);
    }
  };

  const handleAddRelatedIncident = async (e) => {
    e.preventDefault();
    if (!canModifyActiveProject || !relTitle.trim() || !relLink.trim()) return;
    try {
      await api.addRelatedIncident({
        project: activeProject.id,
        title: relTitle.trim(),
        link: relLink.trim(),
        analyst_name: currentAnalystName,
      });
      setRelTitle('');
      setRelLink('');
      await onProjectMutated(activeProject.id);
      onNotifySuccess('Related escalated incident added.');
    } catch (err) {
      onApiError(err, 'Could not add related incident');
    }
  };

  const handleDeleteRelatedIncident = async (id) => {
    if (!canModifyActiveProject) return;
    try {
      await api.deleteRelatedIncident(id);
      await onProjectMutated(activeProject.id);
      onNotifySuccess('Related incident removed.');
    } catch (err) {
      onApiError(err, 'Failed to remove related incident');
    }
  };

  const handleAddContact = async (e) => {
    e.preventDefault();
    if (!canModifyActiveProject || !contactForm.name.trim()) return;
    try {
      await api.addCustomerContact({
        project: activeProject.id,
        name: contactForm.name.trim(),
        role_title: contactForm.role_title.trim(),
        email: contactForm.email.trim(),
        phone: contactForm.phone.trim(),
        notes: contactForm.notes.trim(),
      });
      setContactForm({ name: '', role_title: '', email: '', phone: '', notes: '' });
      await onProjectMutated(activeProject.id);
      onNotifySuccess('Customer contact added.');
    } catch (err) {
      onApiError(err, 'Could not add customer contact');
    }
  };

  const handleDeleteContact = async (id) => {
    if (!canModifyActiveProject) return;
    try {
      await api.deleteCustomerContact(id);
      await onProjectMutated(activeProject.id);
      onNotifySuccess('Customer contact removed.');
    } catch (err) {
      onApiError(err, 'Failed to remove customer contact');
    }
  };

  const relatedIncidents = activeProject.related_incidents || [];
  const customerContacts = activeProject.customer_contacts || [];

  return (
    <>
      {/* 1. Action Plan Section */}
      <Card className="soc-card">
        <Card.Header className="soc-card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div className="d-flex align-items-center gap-2">
            <ClipboardList size={16} className="text-lb-lime" />
            <span>Action Plan &amp; Investigation Next Steps</span>
          </div>
          {canModifyActiveProject && isActionPlanDirty && (
            <Button
              size="sm"
              className="btn-lb-primary"
              disabled={savingActionPlan}
              onClick={handleSaveActionPlan}
            >
              <Save size={14} className="me-1" />
              {savingActionPlan ? 'Saving...' : 'Save Action Plan'}
            </Button>
          )}
        </Card.Header>
        <Card.Body>
          {canModifyActiveProject ? (
            <Form onSubmit={handleSaveActionPlan}>
              <Form.Control
                as="textarea"
                rows={4}
                placeholder="Record analyst next steps, areas requiring deeper investigation, containment tasks, or information required from the customer..."
                value={actionPlanDraft}
                onChange={(e) => setActionPlanDraft(e.target.value)}
              />
              <div className="d-flex justify-content-between align-items-center mt-2">
                <span className="small text-secondary">
                  Visible on the top-level Homepage and inside this investigation.
                </span>
                <Button
                  type="submit"
                  size="sm"
                  className="btn-lb-primary"
                  disabled={!isActionPlanDirty || savingActionPlan}
                >
                  <Save size={13} className="me-1" />
                  {savingActionPlan ? 'Saving...' : 'Save Action Plan'}
                </Button>
              </div>
            </Form>
          ) : (
            <div className="p-3 soc-subbox pre-wrap-text small">
              {activeProject.action_plan || (
                <span className="text-secondary">No action plan recorded.</span>
              )}
            </div>
          )}
        </Card.Body>
      </Card>

      {/* 2. Related Escalated Incidents Section */}
      <Card className="soc-card">
        <Card.Header className="soc-card-header d-flex align-items-center gap-2">
          <Link2 size={16} className="text-lb-cyan" />
          <span>Related Escalated Incidents</span>
        </Card.Header>
        <Card.Body>
          {relatedIncidents.length === 0 ? (
            <div className={`small text-secondary ${canModifyActiveProject ? 'mb-3' : ''}`}>
              No related escalated incidents linked yet.
            </div>
          ) : (
            <ul className={`bullet-list ${canModifyActiveProject ? 'mb-3' : 'mb-0'}`}>
              {relatedIncidents.map((rel) => (
                <li key={rel.id} className="mb-2">
                  <div className="d-flex justify-content-between align-items-start gap-2">
                    <div>
                      <div className="fw-semibold text-white small">{rel.title}</div>
                      <div>
                        <a
                          href={rel.link}
                          target="_blank"
                          rel="noreferrer"
                          className="text-lb-cyan mono-text small text-decoration-none"
                        >
                          {rel.link} <ExternalLink size={12} />
                        </a>
                      </div>
                      {rel.analyst_name && (
                        <div className="text-secondary" style={{ fontSize: '0.72rem' }}>
                          Linked by {rel.analyst_name}
                        </div>
                      )}
                    </div>
                    {canModifyActiveProject && (
                      <Button
                        variant="outline-secondary"
                        size="sm"
                        title="Remove related incident"
                        onClick={() => handleDeleteRelatedIncident(rel.id)}
                      >
                        <Trash2 size={13} />
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {canModifyActiveProject && (
            <Form onSubmit={handleAddRelatedIncident}>
              <Row className="g-2">
                <Col md={5}>
                  <Form.Control
                    size="sm"
                    type="text"
                    required
                    placeholder="Escalated incident title (e.g. EDR-2026-8812: Initial Alert)"
                    value={relTitle}
                    onChange={(e) => setRelTitle(e.target.value)}
                  />
                </Col>
                <Col md={5}>
                  <Form.Control
                    size="sm"
                    type="text"
                    required
                    placeholder="Incident URL (e.g. https://soc.internal.example/tickets/...)"
                    value={relLink}
                    onChange={(e) => setRelLink(e.target.value)}
                  />
                </Col>
                <Col md={2}>
                  <Button type="submit" className="btn-lb-primary w-100" size="sm">
                    <Plus size={14} className="me-1" />
                    Add Link
                  </Button>
                </Col>
              </Row>
            </Form>
          )}
        </Card.Body>
      </Card>

      {/* 3. Key Customer Contacts Section */}
      <Card className="soc-card">
        <Card.Header className="soc-card-header d-flex align-items-center gap-2">
          <UserCheck size={16} className="text-lb-cyan" />
          <span>Key Customer Contacts</span>
        </Card.Header>
        <Card.Body>
          {activeProject.key_customer_contacts && (
            <div className="p-2 px-3 mb-3 soc-subbox small pre-wrap-text">
              <strong className="text-lb-cyan">Bridge / Escalation Notes: </strong>
              {activeProject.key_customer_contacts}
            </div>
          )}

          {customerContacts.length === 0 ? (
            <div className={`small text-secondary ${canModifyActiveProject ? 'mb-3' : ''}`}>
              No key customer contacts recorded yet.
            </div>
          ) : (
            <Table
              responsive
              hover
              size="sm"
              variant="dark"
              className={`align-middle ${canModifyActiveProject ? 'mb-3' : 'mb-0'}`}
            >
              <thead className="small text-secondary text-uppercase">
                <tr>
                  <th>Name</th>
                  <th>Role / Title</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Notes</th>
                  {canModifyActiveProject && <th className="text-end">Remove</th>}
                </tr>
              </thead>
              <tbody className="small">
                {customerContacts.map((c) => (
                  <tr key={c.id}>
                    <td className="fw-semibold text-white">{c.name}</td>
                    <td>{c.role_title || '—'}</td>
                    <td className="mono-text">
                      {c.email ? (
                        <a
                          href={`mailto:${c.email}`}
                          className="text-lb-cyan text-decoration-none"
                        >
                          <Mail size={12} className="me-1" />
                          {c.email}
                        </a>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="mono-text">
                      {c.phone ? (
                        <span>
                          <Phone size={12} className="me-1 text-secondary" />
                          {c.phone}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="text-secondary">{c.notes || '—'}</td>
                    {canModifyActiveProject && (
                      <td className="text-end">
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          onClick={() => handleDeleteContact(c.id)}
                          title="Remove customer contact"
                        >
                          <Trash2 size={13} />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </Table>
          )}

          {canModifyActiveProject && (
            <Form onSubmit={handleAddContact}>
              <Row className="g-2">
                <Col md={3}>
                  <Form.Control
                    size="sm"
                    type="text"
                    required
                    placeholder="Contact Name *"
                    value={contactForm.name}
                    onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                  />
                </Col>
                <Col md={2}>
                  <Form.Control
                    size="sm"
                    type="text"
                    placeholder="Role / Title"
                    value={contactForm.role_title}
                    onChange={(e) =>
                      setContactForm({ ...contactForm, role_title: e.target.value })
                    }
                  />
                </Col>
                <Col md={3}>
                  <Form.Control
                    size="sm"
                    type="email"
                    placeholder="Email"
                    value={contactForm.email}
                    onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                  />
                </Col>
                <Col md={2}>
                  <Form.Control
                    size="sm"
                    type="text"
                    placeholder="Phone"
                    value={contactForm.phone}
                    onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                  />
                </Col>
                <Col md={2}>
                  <Button type="submit" className="btn-lb-primary w-100" size="sm">
                    <Plus size={14} className="me-1" />
                    Add Contact
                  </Button>
                </Col>
                <Col md={12}>
                  <Form.Control
                    size="sm"
                    type="text"
                    placeholder="Contact notes / availability / escalation scope (optional)"
                    value={contactForm.notes}
                    onChange={(e) => setContactForm({ ...contactForm, notes: e.target.value })}
                  />
                </Col>
              </Row>
            </Form>
          )}
        </Card.Body>
      </Card>
    </>
  );
}
