import React, { useState, useRef, useEffect } from 'react';
import { Form, Badge, Button } from 'react-bootstrap';
import { ChevronDown, X } from 'lucide-react';
import {
  MITRE_TACTICS_WITH_TECHNIQUES,
  ALL_MITRE_TACTICS,
  splitMitreValues,
  joinMitreValues,
  findParentTacticForTechnique,
} from './mitreData';

export function MitreTacticsSelect({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapperRef = useRef(null);

  const selected = splitMitreValues(value);

  useEffect(() => {
    const handleOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const toggleItem = (tactic) => {
    const exists = selected.includes(tactic);
    const next = exists ? selected.filter((t) => t !== tactic) : [...selected, tactic];
    onChange(joinMitreValues(next));
  };

  const filteredTactics = ALL_MITRE_TACTICS.filter(
    (t) => !query.trim() || t.toLowerCase().includes(query.trim().toLowerCase()),
  );

  // Include any legacy/custom tactic values already saved on the item
  const customSelected = selected.filter((t) => !ALL_MITRE_TACTICS.includes(t));

  return (
    <div className="position-relative" ref={wrapperRef}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen((prev) => !prev);
          }
        }}
        className="mitre-multiselect-trigger d-flex justify-content-between align-items-center gap-2"
      >
        <div className="d-flex flex-wrap gap-1 align-items-center" style={{ minWidth: 0 }}>
          {selected.length === 0 ? (
            <span className="text-secondary small">Select MITRE Tactic(s)...</span>
          ) : (
            selected.map((t) => (
              <Badge
                key={t}
                bg="dark"
                className="border border-info text-lb-cyan fw-normal d-inline-flex align-items-center gap-1 mitre-badge-wrap"
              >
                <span>{t}</span>
                <X
                  size={12}
                  role="button"
                  className="flex-shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleItem(t);
                  }}
                />
              </Badge>
            ))
          )}
        </div>
        <ChevronDown size={15} className="text-secondary flex-shrink-0" />
      </div>

      {open && (
        <div className="mitre-multiselect-menu shadow-lg p-2 mt-1">
          <div className="d-flex gap-2 mb-2">
            <Form.Control
              size="sm"
              type="text"
              placeholder="Filter tactics..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {selected.length > 0 && (
              <Button
                variant="outline-secondary"
                size="sm"
                type="button"
                onClick={() => onChange('')}
              >
                Clear
              </Button>
            )}
          </div>
          <div className="mitre-multiselect-options">
            {customSelected.map((custom) => (
              <label key={custom} className="mitre-option-row">
                <input
                  type="checkbox"
                  checked
                  onChange={() => toggleItem(custom)}
                  className="form-check-input me-2"
                />
                <span className="small">{custom}</span>
              </label>
            ))}
            {filteredTactics.map((tactic) => (
              <label key={tactic} className="mitre-option-row">
                <input
                  type="checkbox"
                  checked={selected.includes(tactic)}
                  onChange={() => toggleItem(tactic)}
                  className="form-check-input me-2"
                />
                <span className="small">{tactic}</span>
              </label>
            ))}
            {filteredTactics.length === 0 && (
              <div className="text-secondary small py-2 text-center">No matching tactics.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function MitreTechniquesSelect({ tacticValue, value, onChange, onAutoAddTactic }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [showAllTactics, setShowAllTactics] = useState(false);
  const wrapperRef = useRef(null);

  const selectedTactics = splitMitreValues(tacticValue);
  const selectedTechniques = splitMitreValues(value);

  useEffect(() => {
    const handleOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const toggleTechnique = (technique, groupTactic) => {
    const exists = selectedTechniques.includes(technique);
    const next = exists
      ? selectedTechniques.filter((t) => t !== technique)
      : [...selectedTechniques, technique];
    onChange(joinMitreValues(next));

    if (!exists && onAutoAddTactic) {
      const tacticToEnsure = groupTactic || findParentTacticForTechnique(technique);
      if (tacticToEnsure && !selectedTactics.includes(tacticToEnsure)) {
        onAutoAddTactic(joinMitreValues([...selectedTactics, tacticToEnsure]));
      }
    }
  };

  const activeGroups =
    selectedTactics.length > 0 && !showAllTactics
      ? MITRE_TACTICS_WITH_TECHNIQUES.filter((g) => selectedTactics.includes(g.tactic))
      : MITRE_TACTICS_WITH_TECHNIQUES;

  const qLower = query.trim().toLowerCase();
  const filteredGroups = activeGroups
    .map((g) => ({
      tactic: g.tactic,
      techniques: g.techniques.filter(
        (tech) => !qLower || tech.toLowerCase().includes(qLower) || g.tactic.toLowerCase().includes(qLower),
      ),
    }))
    .filter((g) => g.techniques.length > 0);

  const allCatalogTechs = new Set(MITRE_TACTICS_WITH_TECHNIQUES.flatMap((g) => g.techniques));
  const customSelected = selectedTechniques.filter((t) => !allCatalogTechs.has(t));

  return (
    <div className="position-relative" ref={wrapperRef}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen((prev) => !prev);
          }
        }}
        className="mitre-multiselect-trigger d-flex justify-content-between align-items-center gap-2"
      >
        <div className="d-flex flex-wrap gap-1 align-items-center" style={{ minWidth: 0 }}>
          {selectedTechniques.length === 0 ? (
            <span className="text-secondary small">
              {selectedTactics.length > 0
                ? 'Select relevant MITRE Technique(s)...'
                : 'Select MITRE Technique(s)...'}
            </span>
          ) : (
            selectedTechniques.map((tech) => (
              <Badge
                key={tech}
                bg="dark"
                className="border border-secondary text-light mono-text fw-normal d-inline-flex align-items-center gap-1 mitre-badge-wrap"
              >
                <span>{tech}</span>
                <X
                  size={12}
                  role="button"
                  className="flex-shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleTechnique(tech, null);
                  }}
                />
              </Badge>
            ))
          )}
        </div>
        <ChevronDown size={15} className="text-secondary flex-shrink-0" />
      </div>

      {open && (
        <div className="mitre-multiselect-menu shadow-lg p-2 mt-1">
          <div className="d-flex gap-2 mb-2">
            <Form.Control
              size="sm"
              type="text"
              placeholder="Search technique ID or name..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {selectedTechniques.length > 0 && (
              <Button
                variant="outline-secondary"
                size="sm"
                type="button"
                onClick={() => onChange('')}
              >
                Clear
              </Button>
            )}
          </div>

          {selectedTactics.length > 0 && (
            <div className="d-flex justify-content-between align-items-center px-1 mb-2 small text-secondary">
              <span>
                {showAllTactics
                  ? 'Showing all MITRE tactics'
                  : `Filtered by ${selectedTactics.length} selected tactic(s)`}
              </span>
              <button
                type="button"
                className="btn btn-link btn-sm p-0 text-lb-cyan text-decoration-none"
                style={{ fontSize: '0.75rem' }}
                onClick={() => setShowAllTactics((prev) => !prev)}
              >
                {showAllTactics ? 'Filter by selected tactics' : 'Show all tactics'}
              </button>
            </div>
          )}

          <div className="mitre-multiselect-options">
            {customSelected.map((custom) => (
              <label key={custom} className="mitre-option-row">
                <input
                  type="checkbox"
                  checked
                  onChange={() => toggleTechnique(custom, null)}
                  className="form-check-input me-2"
                />
                <span className="small mono-text">{custom}</span>
              </label>
            ))}

            {filteredGroups.map((group) => (
              <div key={group.tactic} className="mb-2">
                <div className="mitre-group-header">{group.tactic}</div>
                {group.techniques.map((tech) => (
                  <label key={`${group.tactic}-${tech}`} className="mitre-option-row">
                    <input
                      type="checkbox"
                      checked={selectedTechniques.includes(tech)}
                      onChange={() => toggleTechnique(tech, group.tactic)}
                      className="form-check-input me-2"
                    />
                    <span className="small mono-text">{tech}</span>
                  </label>
                ))}
              </div>
            ))}

            {filteredGroups.length === 0 && (
              <div className="text-secondary small py-2 text-center">No matching techniques.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
