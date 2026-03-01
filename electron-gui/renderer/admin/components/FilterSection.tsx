import React, { useState, useEffect } from 'react';

interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

interface FilterField {
  key: string;
  label: string;
  type: 'select' | 'multiselect' | 'text' | 'date' | 'daterange' | 'number' | 'boolean';
  options?: FilterOption[];
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
}

interface FilterSectionProps {
  fields: FilterField[];
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
  onReset?: () => void;
  onApply?: () => void;
  loading?: boolean;
  className?: string;
}

export const FilterSection: React.FC<FilterSectionProps> = ({
  fields,
  values,
  onChange,
  onReset,
  onApply,
  loading = false,
  className = ''
}) => {
  const [localValues, setLocalValues] = useState<Record<string, any>>(values);

  useEffect(() => {
    setLocalValues(values);
  }, [values]);

  const handleFieldChange = (key: string, value: any) => {
    const newValues = { ...localValues, [key]: value };
    setLocalValues(newValues);
    onChange(newValues);
  };

  const handleReset = () => {
    const resetValues: Record<string, any> = {};
    fields.forEach(field => {
      switch (field.type) {
        case 'multiselect':
        case 'boolean':
          resetValues[field.key] = field.type === 'boolean' ? false : [];
          break;
        case 'number':
          resetValues[field.key] = '';
          break;
        default:
          resetValues[field.key] = '';
      }
    });
    setLocalValues(resetValues);
    onChange(resetValues);
    onReset?.();
  };

  const handleApply = () => {
    onApply?.();
  };

  const renderField = (field: FilterField) => {
    const value = localValues[field.key] || '';

    switch (field.type) {
      case 'select':
        return (
          <div key={field.key} className="filter-field">
            <label htmlFor={field.key}>{field.label}</label>
            <select
              id={field.key}
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              disabled={loading}
            >
              <option value="">All {field.label}</option>
              {field.options?.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} {option.count !== undefined ? `(${option.count})` : ''}
                </option>
              ))}
            </select>
          </div>
        );

      case 'multiselect':
        return (
          <div key={field.key} className="filter-field">
            <label htmlFor={field.key}>{field.label}</label>
            <div className="multiselect-container">
              {field.options?.map((option) => (
                <label key={option.value} className="multiselect-option">
                  <input
                    type="checkbox"
                    checked={Array.isArray(value) && value.includes(option.value)}
                    onChange={(e) => {
                      const currentValues = Array.isArray(value) ? value : [];
                      const newValues = e.target.checked
                        ? [...currentValues, option.value]
                        : currentValues.filter(v => v !== option.value);
                      handleFieldChange(field.key, newValues);
                    }}
                    disabled={loading}
                  />
                  <span className="option-label">
                    {option.label} {option.count !== undefined ? `(${option.count})` : ''}
                  </span>
                </label>
              ))}
            </div>
          </div>
        );

      case 'text':
        return (
          <div key={field.key} className="filter-field">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="text"
              id={field.key}
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              disabled={loading}
            />
          </div>
        );

      case 'date':
        return (
          <div key={field.key} className="filter-field">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="date"
              id={field.key}
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              disabled={loading}
            />
          </div>
        );

      case 'daterange':
        return (
          <div key={field.key} className="filter-field daterange">
            <label>{field.label}</label>
            <div className="daterange-inputs">
              <input
                type="date"
                value={value?.start || ''}
                onChange={(e) => handleFieldChange(field.key, { 
                  ...value, 
                  start: e.target.value 
                })}
                placeholder="Start date"
                disabled={loading}
              />
              <span className="daterange-separator">to</span>
              <input
                type="date"
                value={value?.end || ''}
                onChange={(e) => handleFieldChange(field.key, { 
                  ...value, 
                  end: e.target.value 
                })}
                placeholder="End date"
                disabled={loading}
              />
            </div>
          </div>
        );

      case 'number':
        return (
          <div key={field.key} className="filter-field">
            <label htmlFor={field.key}>{field.label}</label>
            <input
              type="number"
              id={field.key}
              value={value}
              onChange={(e) => handleFieldChange(field.key, e.target.value)}
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
              step={field.step}
              disabled={loading}
            />
          </div>
        );

      case 'boolean':
        return (
          <div key={field.key} className="filter-field boolean">
            <label className="boolean-label">
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => handleFieldChange(field.key, e.target.checked)}
                disabled={loading}
              />
              <span className="boolean-text">{field.label}</span>
            </label>
          </div>
        );

      default:
        return null;
    }
  };

  const hasActiveFilters = () => {
    return Object.values(localValues).some(value => {
      if (Array.isArray(value)) return value.length > 0;
      if (typeof value === 'boolean') return value;
      return value !== '' && value != null;
    });
  };

  return (
    <div className={`filter-section ${className}`}>
      <div className="filter-header">
        <h4>Filters</h4>
        <div className="filter-actions">
          {hasActiveFilters() && (
            <button 
              className="btn secondary small"
              onClick={handleReset}
              disabled={loading}
            >
              Clear All
            </button>
          )}
          {onApply && (
            <button 
              className="btn primary small"
              onClick={handleApply}
              disabled={loading}
            >
              Apply
            </button>
          )}
        </div>
      </div>

      <div className="filter-fields">
        {fields.map(renderField)}
      </div>

      {loading && (
        <div className="filter-loading">
          <div className="loading-spinner"></div>
          <span>Loading filters...</span>
        </div>
      )}
    </div>
  );
};

export default FilterSection;
