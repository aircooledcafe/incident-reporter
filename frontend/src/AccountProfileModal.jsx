import React, { useState, useEffect } from 'react';
import { Modal, Form, Row, Col, Button, InputGroup, Nav } from 'react-bootstrap';
import { RefreshCw, Upload, Trash2 } from 'lucide-react';
import { api } from './api';

const PRONOUN_SUGGESTIONS = [
  'she/her',
  'he/him',
  'they/them',
  'she/they',
  'he/they',
  'any pronouns',
];

function getInitials(user) {
  const src = user?.display_name || user?.username || '?';
  const parts = src.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return src.slice(0, 2).toUpperCase();
}

export default function AccountProfileModal({
  show,
  onHide,
  authUser,
  roleLabel,
  canEditRole,
  onProfileUpdated,
  onNotifySuccess,
  onApiError,
}) {
  const [tab, setTab] = useState('profile'); // 'profile' | 'security'

  // Profile fields
  const [preferredDisplayName, setPreferredDisplayName] = useState('');
  const [pronouns, setPronouns] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreviewUrl, setAvatarPreviewUrl] = useState('');
  const [removeAvatar, setRemoveAvatar] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  // Password & API token fields
  const [ownPasswordForm, setOwnPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [apiTokenValue, setApiTokenValue] = useState('');
  const [apiTokenLoading, setApiTokenLoading] = useState(false);

  useEffect(() => {
    if (show && authUser) {
      setTab('profile');
      setPreferredDisplayName(authUser.preferred_display_name || '');
      setPronouns(authUser.pronouns || '');
      setFirstName(authUser.first_name || '');
      setLastName(authUser.last_name || '');
      setEmail(authUser.email || '');
      setAvatarFile(null);
      setAvatarPreviewUrl('');
      setRemoveAvatar(false);
      setOwnPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });

      if (canEditRole) {
        setApiTokenLoading(true);
        api
          .getApiToken()
          .then((res) => setApiTokenValue(res.token || ''))
          .catch(() => setApiTokenValue(''))
          .finally(() => setApiTokenLoading(false));
      }
    }
  }, [show, authUser, canEditRole]);

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreviewUrl('');
      return undefined;
    }
    const objectUrl = URL.createObjectURL(avatarFile);
    setAvatarPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [avatarFile]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    try {
      setSavingProfile(true);
      const formData = new FormData();
      formData.append('preferred_display_name', preferredDisplayName.trim());
      formData.append('pronouns', pronouns.trim());
      formData.append('first_name', firstName.trim());
      formData.append('last_name', lastName.trim());
      formData.append('email', email.trim());
      if (removeAvatar) {
        formData.append('remove_avatar', 'true');
      }
      if (avatarFile) {
        formData.append('avatar', avatarFile);
      }

      const updatedUser = await api.updateProfile(formData);
      onProfileUpdated(updatedUser);
      setAvatarFile(null);
      setRemoveAvatar(false);
      onNotifySuccess('Profile preferences updated.');
    } catch (err) {
      onApiError(err, 'Could not update profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangeOwnPassword = async (e) => {
    e.preventDefault();
    if (ownPasswordForm.new_password !== ownPasswordForm.confirm_password) {
      onApiError(new Error('New password and confirmation do not match.'), 'Validation');
      return;
    }
    try {
      await api.changeOwnPassword({
        current_password: ownPasswordForm.current_password,
        new_password: ownPasswordForm.new_password,
      });
      setOwnPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      onNotifySuccess('Your password has been updated.');
    } catch (err) {
      onApiError(err, 'Could not change password');
    }
  };

  const handleRotateApiToken = async () => {
    try {
      setApiTokenLoading(true);
      const res = await api.rotateApiToken();
      setApiTokenValue(res.token || '');
      onNotifySuccess('SOC ingestion API token rotated.');
    } catch (err) {
      onApiError(err, 'Failed to rotate API token');
    } finally {
      setApiTokenLoading(false);
    }
  };

  if (!authUser) return null;

  const effectiveAvatarUrl = removeAvatar
    ? ''
    : avatarPreviewUrl || authUser.avatar_url || '';

  return (
    <Modal show={show} onHide={onHide} size="lg" transition={false} centered>
      <Modal.Header closeButton className="bg-dark border-secondary">
        <Modal.Title className="fs-6">
          Account &amp; Profile Options — {authUser.username} ({roleLabel})
        </Modal.Title>
      </Modal.Header>
      <Modal.Body className="bg-dark">
        <datalist id="pronoun-presets-list">
          {PRONOUN_SUGGESTIONS.map((p) => (
            <option key={p} value={p} />
          ))}
        </datalist>

        <Nav
          variant="tabs"
          className="mb-3"
          activeKey={tab}
          onSelect={(k) => setTab(k || 'profile')}
        >
          <Nav.Item>
            <Nav.Link eventKey="profile">Profile, Avatar &amp; Pronouns</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="security">Password &amp; API Token</Nav.Link>
          </Nav.Item>
        </Nav>

        {tab === 'profile' ? (
          <Form onSubmit={handleSaveProfile}>
            {/* Avatar Section */}
            <div className="d-flex flex-wrap align-items-center gap-3 p-3 mb-3 soc-subbox">
              {effectiveAvatarUrl ? (
                <img
                  src={effectiveAvatarUrl}
                  alt={authUser.display_name || authUser.username}
                  className="user-avatar-lg"
                />
              ) : (
                <div className="user-avatar-lg">{getInitials(authUser)}</div>
              )}

              <div className="flex-grow-1">
                <div className="fw-semibold text-white">
                  {preferredDisplayName.trim() ||
                    `${firstName} ${lastName}`.trim() ||
                    authUser.username}
                  {pronouns.trim() && (
                    <span className="text-secondary fw-normal ms-2 small">
                      ({pronouns.trim()})
                    </span>
                  )}
                </div>
                <div className="small text-secondary mb-2">
                  Upload a profile avatar (PNG, JPG, GIF, WebP up to 5 MB). Stored in persistent external artifacts storage.
                </div>
                <div className="d-flex flex-wrap align-items-center gap-2">
                  <label className="btn btn-sm btn-lb-cyan mb-0" style={{ cursor: 'pointer' }}>
                    <Upload size={13} className="me-1" />
                    Choose Avatar Image
                    <input
                      type="file"
                      accept="image/*"
                      hidden
                      onChange={(e) => {
                        const file = e.target.files && e.target.files[0];
                        if (file) {
                          setAvatarFile(file);
                          setRemoveAvatar(false);
                        }
                      }}
                    />
                  </label>

                  {(authUser.avatar_url || avatarFile) && !removeAvatar && (
                    <Button
                      type="button"
                      variant="outline-danger"
                      size="sm"
                      onClick={() => {
                        setAvatarFile(null);
                        setRemoveAvatar(true);
                      }}
                    >
                      <Trash2 size={13} className="me-1" />
                      Remove Avatar
                    </Button>
                  )}
                </div>
              </div>
            </div>

            <Row className="g-3">
              <Col md={7}>
                <Form.Group>
                  <Form.Label className="small">Preferred Display Name</Form.Label>
                  <Form.Control
                    type="text"
                    placeholder="e.g. Alex Rivera"
                    value={preferredDisplayName}
                    onChange={(e) => setPreferredDisplayName(e.target.value)}
                  />
                  <Form.Text className="text-secondary" style={{ fontSize: '0.74rem' }}>
                    Displayed in the navigation bar, analyst attribution, and team directory.
                  </Form.Text>
                </Form.Group>
              </Col>

              <Col md={5}>
                <Form.Group>
                  <Form.Label className="small">Pronouns</Form.Label>
                  <Form.Control
                    type="text"
                    list="pronoun-presets-list"
                    placeholder="e.g. they/them, she/her, he/him"
                    value={pronouns}
                    onChange={(e) => setPronouns(e.target.value)}
                  />
                </Form.Group>
              </Col>

              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">First Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                  />
                </Form.Group>
              </Col>

              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">Last Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                  />
                </Form.Group>
              </Col>

              <Col md={4}>
                <Form.Group>
                  <Form.Label className="small">Email</Form.Label>
                  <Form.Control
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </Form.Group>
              </Col>
            </Row>

            <div className="mt-4 d-flex justify-content-end gap-2">
              <Button variant="outline-secondary" size="sm" type="button" onClick={onHide}>
                Close
              </Button>
              <Button className="btn-lb-primary" size="sm" type="submit" disabled={savingProfile}>
                {savingProfile ? 'Saving...' : 'Save Profile Preferences'}
              </Button>
            </div>
          </Form>
        ) : (
          <div>
            <Form onSubmit={handleChangeOwnPassword} className="mb-3">
              <div className="fw-semibold small text-lb-cyan mb-2">Change Your Password</div>
              <Row className="g-2">
                <Col md={12}>
                  <Form.Group className="mb-2">
                    <Form.Label className="small">Current Password</Form.Label>
                    <Form.Control
                      type="password"
                      required
                      value={ownPasswordForm.current_password}
                      onChange={(e) =>
                        setOwnPasswordForm({
                          ...ownPasswordForm,
                          current_password: e.target.value,
                        })
                      }
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-2">
                    <Form.Label className="small">New Password</Form.Label>
                    <Form.Control
                      type="password"
                      required
                      value={ownPasswordForm.new_password}
                      onChange={(e) =>
                        setOwnPasswordForm({ ...ownPasswordForm, new_password: e.target.value })
                      }
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-2">
                    <Form.Label className="small">Confirm New Password</Form.Label>
                    <Form.Control
                      type="password"
                      required
                      value={ownPasswordForm.confirm_password}
                      onChange={(e) =>
                        setOwnPasswordForm({
                          ...ownPasswordForm,
                          confirm_password: e.target.value,
                        })
                      }
                    />
                  </Form.Group>
                </Col>
              </Row>
              <Button type="submit" className="btn-lb-primary mt-2" size="sm">
                Update Password
              </Button>
            </Form>

            {canEditRole && (
              <div className="pt-3 border-top border-secondary">
                <div className="fw-semibold small text-lb-cyan mb-1">
                  Programmatic SOC Ingestion API Token
                </div>
                <p className="text-secondary small mb-2">
                  Pass <code>Authorization: Token &lt;token&gt;</code> when posting automated SIEM /
                  SOAR / IDS events to <code>/api/soc/ingest/</code>.
                </p>
                <InputGroup size="sm">
                  <Form.Control
                    type="text"
                    readOnly
                    className="mono-text bg-dark text-light border-secondary"
                    value={apiTokenLoading ? 'Loading...' : apiTokenValue}
                  />
                  <Button
                    variant="outline-warning"
                    onClick={handleRotateApiToken}
                    disabled={apiTokenLoading}
                    title="Generate a new token and invalidate the current one"
                  >
                    <RefreshCw size={13} className="me-1" />
                    Rotate
                  </Button>
                </InputGroup>
              </div>
            )}
          </div>
        )}
      </Modal.Body>
    </Modal>
  );
}
