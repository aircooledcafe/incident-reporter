import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Form,
  Badge,
  Spinner,
  Alert,
  Row,
  Col,
} from 'react-bootstrap';
import {
  Building2,
  Users,
  Plus,
  Trash2,
  Edit2,
  Phone,
  Mail,
  ShieldAlert,
  Search,
  CheckCircle,
  X,
} from 'lucide-react';
import { api } from './api';

const ESCALATION_TIERS = [
  { value: 'PRIMARY', label: 'Primary', variant: 'danger' },
  { value: 'SECONDARY', label: 'Secondary', variant: 'warning' },
  { value: 'TERTIARY', label: 'Tertiary', variant: 'info' },
];

export default function CustomerManagementModal({
  show,
  onHide,
  canManage = true,
  onNotifySuccess,
  onNotifyError,
  onCustomerUpdated,
  onCustomerCreated,
}) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Customer create/edit state
  const [showCustomerForm, setShowCustomerForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [customerForm, setCustomerForm] = useState({
    name: '',
    customer_id: '',
    notes: '',
  });

  // Contact create/edit state
  const [showContactForm, setShowContactForm] = useState(false);
  const [targetCustomerForContact, setTargetCustomerForContact] = useState(null);
  const [editingContact, setEditingContact] = useState(null);
  const [contactForm, setContactForm] = useState({
    name: '',
    role_title: '',
    email: '',
    phone: '',
    escalation_tier: 'PRIMARY',
    notes: '',
  });

  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const loadCustomers = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await api.listCustomers();
      setCustomers(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load customers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (show) {
      loadCustomers();
      setShowCustomerForm(false);
      setShowContactForm(false);
    }
  }, [show]);

  // Customer Form handlers
  const handleOpenNewCustomer = () => {
    setEditingCustomer(null);
    setCustomerForm({ name: '', customer_id: '', notes: '' });
    setShowCustomerForm(true);
  };

  const handleOpenEditCustomer = (cust) => {
    setEditingCustomer(cust);
    setCustomerForm({
      name: cust.name || '',
      customer_id: cust.customer_id || '',
      notes: cust.notes || '',
    });
    setShowCustomerForm(true);
  };

  const handleSaveCustomer = async (e) => {
    e.preventDefault();
    if (!customerForm.name.trim()) {
      setErrorMsg('Customer name is required.');
      return;
    }
    if (!customerForm.customer_id.trim()) {
      setErrorMsg('Customer ID code (e.g. ACME-CORP) is required.');
      return;
    }

    setSaving(true);
    setErrorMsg('');
    try {
      if (editingCustomer) {
        await api.updateCustomer(editingCustomer.id, customerForm);
        onNotifySuccess?.(`Customer "${customerForm.name}" updated.`);
      } else {
        const created = await api.createCustomer(customerForm);
        onNotifySuccess?.(`Customer "${customerForm.name}" created.`);
        onCustomerCreated?.(created);
      }
      setShowCustomerForm(false);
      await loadCustomers();
      onCustomerUpdated?.();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save customer');
      onNotifyError?.(err.message || 'Failed to save customer');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCustomer = async (cust) => {
    if (cust.investigations_count > 0) {
      alert(`Cannot delete "${cust.name}" because it is associated with ${cust.investigations_count} investigation(s).`);
      return;
    }
    if (!window.confirm(`Are you sure you want to delete customer "${cust.name}"?`)) {
      return;
    }

    try {
      await api.deleteCustomer(cust.id);
      onNotifySuccess?.(`Customer "${cust.name}" deleted.`);
      await loadCustomers();
      onCustomerUpdated?.();
    } catch (err) {
      onNotifyError?.(err.message || 'Failed to delete customer');
    }
  };

  // Contact Form handlers
  const handleOpenNewContact = (cust) => {
    setTargetCustomerForContact(cust);
    setEditingContact(null);
    setContactForm({
      name: '',
      role_title: '',
      email: '',
      phone: '',
      escalation_tier: 'PRIMARY',
      notes: '',
    });
    setShowContactForm(true);
  };

  const handleOpenEditContact = (cust, contact) => {
    setTargetCustomerForContact(cust);
    setEditingContact(contact);
    setContactForm({
      name: contact.name || '',
      role_title: contact.role_title || '',
      email: contact.email || '',
      phone: contact.phone || '',
      escalation_tier: contact.escalation_tier || 'PRIMARY',
      notes: contact.notes || '',
    });
    setShowContactForm(true);
  };

  const handleSaveContact = async (e) => {
    e.preventDefault();
    if (!contactForm.name.trim()) {
      setErrorMsg('Contact name is required.');
      return;
    }

    setSaving(true);
    setErrorMsg('');
    try {
      const payload = {
        ...contactForm,
        customer: targetCustomerForContact.id,
      };
      if (editingContact) {
        await api.updateCustomerContact(editingContact.id, payload);
        onNotifySuccess?.(`Contact "${contactForm.name}" updated.`);
      } else {
        await api.addCustomerContact(payload);
        onNotifySuccess?.(`Contact "${contactForm.name}" added to ${targetCustomerForContact.name}.`);
      }
      setShowContactForm(false);
      await loadCustomers();
      onCustomerUpdated?.();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save contact');
      onNotifyError?.(err.message || 'Failed to save contact');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteContact = async (contact) => {
    if (!window.confirm(`Delete contact "${contact.name}"?`)) {
      return;
    }
    try {
      await api.deleteCustomerContact(contact.id);
      onNotifySuccess?.('Contact removed.');
      await loadCustomers();
      onCustomerUpdated?.();
    } catch (err) {
      onNotifyError?.(err.message || 'Failed to remove contact');
    }
  };

  const filteredCustomers = customers.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (c.name && c.name.toLowerCase().includes(q)) ||
      (c.customer_id && c.customer_id.toLowerCase().includes(q)) ||
      (c.notes && c.notes.toLowerCase().includes(q))
    );
  });

  return (
    <>
      <Modal
        show={show && !showCustomerForm && !showContactForm}
        onHide={onHide}
        size="xl"
        centered
        className="soc-editor-modal evidence-detail-modal"
      >
        <Modal.Header closeButton closeVariant="white">
          <Modal.Title className="d-flex align-items-center gap-2">
            <Building2 size={20} className="text-primary" />
            <span>Customer Directory & Contact Escalations</span>
          </Modal.Title>
        </Modal.Header>

        <Modal.Body className="p-4" style={{ maxHeight: '78vh', overflowY: 'auto' }}>
          {errorMsg && (
            <Alert variant="danger" dismissible onClose={() => setErrorMsg('')}>
              {errorMsg}
            </Alert>
          )}

          <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center mb-4">
            <div className="position-relative flex-grow-1" style={{ maxWidth: '400px' }}>
              <Search
                size={16}
                className="position-absolute text-muted"
                style={{ top: '10px', left: '12px' }}
              />
              <Form.Control
                type="text"
                placeholder="Search customers by name or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ paddingLeft: '36px' }}
                className="bg-dark text-light border-secondary"
              />
            </div>

            {canManage && (
              <Button
                variant="primary"
                size="sm"
                className="d-flex align-items-center gap-2"
                onClick={handleOpenNewCustomer}
              >
                <Plus size={16} />
                <span>Add Customer</span>
              </Button>
            )}
          </div>

          {loading ? (
            <div className="text-center py-5">
              <Spinner animation="border" variant="primary" />
              <p className="text-muted mt-2">Loading customer directory...</p>
            </div>
          ) : filteredCustomers.length === 0 ? (
            <div className="text-center py-5 soc-subbox">
              <Building2 size={36} className="text-muted mb-2" />
              <p className="text-light mb-1">No customers found</p>
              <p className="text-muted small">
                {searchQuery
                  ? 'No client organizations match your search query.'
                  : 'Get started by creating your first customer organization.'}
              </p>
              {canManage && (
                <Button
                  variant="outline-primary"
                  size="sm"
                  className="mt-2"
                  onClick={handleOpenNewCustomer}
                >
                  <Plus size={14} className="me-1" /> Create Customer
                </Button>
              )}
            </div>
          ) : (
            <div className="d-flex flex-column gap-3">
              {filteredCustomers.map((cust) => (
                <div key={cust.id} className="soc-subbox p-3 rounded">
                  <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
                    <div>
                      <div className="d-flex align-items-center gap-2">
                        <span className="fw-bold text-light fs-5">{cust.name}</span>
                        <Badge bg="secondary" className="mono-text">
                          {cust.customer_id}
                        </Badge>
                        <Badge bg="dark" className="border border-secondary text-info">
                          {cust.investigations_count || 0} Investigations
                        </Badge>
                      </div>
                      {cust.notes && (
                        <p className="text-muted small mt-1 mb-0">{cust.notes}</p>
                      )}
                    </div>

                    {canManage && (
                      <div className="d-flex gap-2">
                        <Button
                          variant="outline-info"
                          size="sm"
                          className="py-1 px-2"
                          onClick={() => handleOpenNewContact(cust)}
                          title="Add Contact"
                        >
                          <Plus size={14} className="me-1" /> Add Contact
                        </Button>
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          className="py-1 px-2"
                          onClick={() => handleOpenEditCustomer(cust)}
                          title="Edit Customer Details"
                        >
                          <Edit2 size={14} />
                        </Button>
                        <Button
                          variant="outline-danger"
                          size="sm"
                          className="py-1 px-2"
                          disabled={cust.investigations_count > 0}
                          onClick={() => handleDeleteCustomer(cust)}
                          title={
                            cust.investigations_count > 0
                              ? 'Cannot delete customer with active investigations'
                              : 'Delete Customer'
                          }
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* Customer Contacts Section */}
                  <div className="mt-3 pt-2 border-top border-secondary">
                    <div className="d-flex align-items-center justify-content-between mb-2">
                      <span className="small text-uppercase tracking-wider text-muted fw-semibold d-flex align-items-center gap-1">
                        <Users size={14} /> Escalation Contacts ({cust.contacts?.length || 0})
                      </span>
                    </div>

                    {!cust.contacts || cust.contacts.length === 0 ? (
                      <div className="text-muted small py-2 fst-italic">
                        No contacts registered for this customer yet.
                      </div>
                    ) : (
                      <Row className="g-2">
                        {cust.contacts.map((contact) => {
                          const tier = ESCALATION_TIERS.find(
                            (t) => t.value === contact.escalation_tier
                          ) || ESCALATION_TIERS[0];
                          return (
                            <Col md={6} lg={4} key={contact.id}>
                              <div
                                className="p-2 rounded bg-dark border border-secondary h-100 position-relative d-flex flex-column justify-content-between"
                                style={{ fontSize: '0.875rem' }}
                              >
                                <div>
                                  <div className="d-flex justify-content-between align-items-start gap-1">
                                    <span className="fw-semibold text-light">
                                      {contact.name}
                                    </span>
                                    <Badge
                                      bg={tier.variant}
                                      className={tier.variant === 'warning' ? 'text-dark' : ''}
                                      style={{ fontSize: '0.68rem' }}
                                    >
                                      {tier.label}
                                    </Badge>
                                  </div>

                                  {contact.role_title && (
                                    <div className="text-muted small">
                                      {contact.role_title}
                                    </div>
                                  )}

                                  <div className="mt-2 space-y-1">
                                    {contact.email && (
                                      <div className="text-light d-flex align-items-center gap-1 small text-truncate">
                                        <Mail size={12} className="text-muted flex-shrink-0" />
                                        <a
                                          href={`mailto:${contact.email}`}
                                          className="text-info text-decoration-none text-truncate"
                                        >
                                          {contact.email}
                                        </a>
                                      </div>
                                    )}
                                    {contact.phone && (
                                      <div className="text-light d-flex align-items-center gap-1 small">
                                        <Phone size={12} className="text-muted flex-shrink-0" />
                                        <span>{contact.phone}</span>
                                      </div>
                                    )}
                                  </div>

                                  {contact.notes && (
                                    <div className="text-muted small mt-1 fst-italic border-top border-secondary pt-1">
                                      {contact.notes}
                                    </div>
                                  )}
                                </div>

                                {canManage && (
                                  <div className="d-flex justify-content-end gap-1 mt-2 pt-1 border-top border-secondary">
                                    <Button
                                      variant="link"
                                      size="sm"
                                      className="p-0 text-muted hover-light"
                                      onClick={() => handleOpenEditContact(cust, contact)}
                                      title="Edit Contact"
                                    >
                                      <Edit2 size={12} />
                                    </Button>
                                    <Button
                                      variant="link"
                                      size="sm"
                                      className="p-0 text-danger ms-2"
                                      onClick={() => handleDeleteContact(contact)}
                                      title="Remove Contact"
                                    >
                                      <Trash2 size={12} />
                                    </Button>
                                  </div>
                                )}
                              </div>
                            </Col>
                          );
                        })}
                      </Row>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Modal.Body>

        <Modal.Footer>
          <Button variant="secondary" onClick={onHide}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Customer Create/Edit Sub-Modal */}
      <Modal
        show={showCustomerForm}
        onHide={() => setShowCustomerForm(false)}
        size="md"
        centered
        className="soc-editor-modal"
      >
        <Modal.Header closeButton closeVariant="white">
          <Modal.Title className="d-flex align-items-center gap-2">
            <Building2 size={18} className="text-primary" />
            <span>{editingCustomer ? 'Edit Customer' : 'New Customer'}</span>
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveCustomer}>
          <Modal.Body className="p-3">
            {errorMsg && (
              <Alert variant="danger" dismissible onClose={() => setErrorMsg('')}>
                {errorMsg}
              </Alert>
            )}

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">
                Customer / Organization Name <span className="text-danger">*</span>
              </Form.Label>
              <Form.Control
                type="text"
                required
                placeholder="e.g. Acme Corporation"
                value={customerForm.name}
                onChange={(e) => setCustomerForm({ ...customerForm, name: e.target.value })}
                className="bg-dark text-light border-secondary"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">
                Customer Identifier / Code <span className="text-danger">*</span>
              </Form.Label>
              <Form.Control
                type="text"
                required
                placeholder="e.g. ACME-CORP or CUST-104"
                value={customerForm.customer_id}
                onChange={(e) => setCustomerForm({ ...customerForm, customer_id: e.target.value })}
                className="bg-dark text-light border-secondary mono-text"
              />
              <Form.Text className="text-muted">
                Unique identifier used across reports and folder prefixes.
              </Form.Text>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">Notes / Scope</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                placeholder="Primary SLA tier, portal links, or engagement scope..."
                value={customerForm.notes}
                onChange={(e) => setCustomerForm({ ...customerForm, notes: e.target.value })}
                className="bg-dark text-light border-secondary"
              />
            </Form.Group>
          </Modal.Body>

          <Modal.Footer>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowCustomerForm(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              type="submit"
              disabled={saving}
            >
              {saving ? 'Saving...' : editingCustomer ? 'Update Customer' : 'Create Customer'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Contact Create/Edit Sub-Modal */}
      <Modal
        show={showContactForm}
        onHide={() => setShowContactForm(false)}
        size="md"
        centered
        className="soc-editor-modal"
      >
        <Modal.Header closeButton closeVariant="white">
          <Modal.Title className="d-flex align-items-center gap-2">
            <Users size={18} className="text-primary" />
            <span>
              {editingContact ? 'Edit Contact' : `Add Contact for ${targetCustomerForContact?.name}`}
            </span>
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSaveContact}>
          <Modal.Body className="p-3">
            {errorMsg && (
              <Alert variant="danger" dismissible onClose={() => setErrorMsg('')}>
                {errorMsg}
              </Alert>
            )}

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">
                Contact Name <span className="text-danger">*</span>
              </Form.Label>
              <Form.Control
                type="text"
                required
                placeholder="e.g. Jane Doe"
                value={contactForm.name}
                onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                className="bg-dark text-light border-secondary"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">
                Escalation Tier <span className="text-danger">*</span>
              </Form.Label>
              <Form.Select
                value={contactForm.escalation_tier}
                onChange={(e) => setContactForm({ ...contactForm, escalation_tier: e.target.value })}
                className="bg-dark text-light border-secondary"
              >
                {ESCALATION_TIERS.map((tier) => (
                  <option key={tier.value} value={tier.value}>
                    {tier.label} Escalation Contact
                  </option>
                ))}
              </Form.Select>
              <Form.Text className="text-muted">
                Primary (1st on-call bridge), Secondary (backup/incident commander), Tertiary (stakeholder).
              </Form.Text>
            </Form.Group>

            <Row className="g-2 mb-3">
              <Col md={6}>
                <Form.Label className="small fw-semibold text-light">Role / Title</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="e.g. CISO, SOC Lead"
                  value={contactForm.role_title}
                  onChange={(e) => setContactForm({ ...contactForm, role_title: e.target.value })}
                  className="bg-dark text-light border-secondary"
                />
              </Col>
              <Col md={6}>
                <Form.Label className="small fw-semibold text-light">Phone</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="+1-555-0199"
                  value={contactForm.phone}
                  onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                  className="bg-dark text-light border-secondary mono-text"
                />
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">Email Address</Form.Label>
              <Form.Control
                type="email"
                placeholder="contact@customer.example"
                value={contactForm.email}
                onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                className="bg-dark text-light border-secondary mono-text"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="small fw-semibold text-light">Availability / Notes</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                placeholder="e.g. Available 24/7 on cell; bridge password in vault"
                value={contactForm.notes}
                onChange={(e) => setContactForm({ ...contactForm, notes: e.target.value })}
                className="bg-dark text-light border-secondary"
              />
            </Form.Group>
          </Modal.Body>

          <Modal.Footer>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowContactForm(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              type="submit"
              disabled={saving}
            >
              {saving ? 'Saving...' : editingContact ? 'Update Contact' : 'Add Contact'}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
}
