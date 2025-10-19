import React, { useState, useCallback } from 'react';

interface User {
  id: string;
  email: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
}

interface CreateSessionPageProps {
  user: User | null;
  onRouteChange: (routeId: string) => void;
  onNotification: (notification: any) => void;
  apiCall: (endpoint: string, method: string, data?: any) => Promise<any>;
}

interface SessionFormData {
  name: string;
  description: string;
  data: string;
  encryption_enabled: boolean;
  auto_anchor: boolean;
  chunk_size: number;
  priority: 'low' | 'normal' | 'high';
}

export const CreateSessionPage: React.FC<CreateSessionPageProps> = ({
  user,
  onRouteChange,
  onNotification,
  apiCall
}) => {
  const [formData, setFormData] = useState<SessionFormData>({
    name: '',
    description: '',
    data: '',
    encryption_enabled: true,
    auto_anchor: false,
    chunk_size: 1024,
    priority: 'normal'
  });
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Handle form input changes
  const handleInputChange = useCallback((field: keyof SessionFormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  }, [validationErrors]);

  // Validate form data
  const validateForm = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Session name is required';
    } else if (formData.name.length > 100) {
      errors.name = 'Session name must be less than 100 characters';
    }

    if (!formData.data.trim()) {
      errors.data = 'Session data is required';
    } else if (formData.data.length > 10 * 1024 * 1024) { // 10MB limit
      errors.data = 'Session data must be less than 10MB';
    }

    if (formData.description.length > 500) {
      errors.description = 'Description must be less than 500 characters';
    }

    if (formData.chunk_size < 512 || formData.chunk_size > 8192) {
      errors.chunk_size = 'Chunk size must be between 512 and 8192 bytes';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formData]);

  // Handle file upload
  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      onNotification({
        type: 'error',
        title: 'File Too Large',
        message: 'File size must be less than 10MB'
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      handleInputChange('data', content);
      handleInputChange('name', file.name);
    };
    reader.readAsText(file);
  }, [onNotification, handleInputChange]);

  // Handle drag and drop
  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);

    const file = event.dataTransfer.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      onNotification({
        type: 'error',
        title: 'File Too Large',
        message: 'File size must be less than 10MB'
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      handleInputChange('data', content);
      handleInputChange('name', file.name);
    };
    reader.readAsText(file);
  }, [onNotification, handleInputChange]);

  // Handle form submission
  const handleSubmit = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      const response = await apiCall('/sessions', 'POST', {
        name: formData.name,
        description: formData.description,
        data: formData.data,
        encryption_enabled: formData.encryption_enabled,
        auto_anchor: formData.auto_anchor,
        chunk_size: formData.chunk_size,
        priority: formData.priority
      });

      if (response.success) {
        onNotification({
          type: 'success',
          title: 'Session Created',
          message: `Session "${formData.name}" created successfully`
        });
        onRouteChange('sessions');
      } else {
        throw new Error(response.message || 'Failed to create session');
      }
    } catch (err) {
      console.error('Failed to create session:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: err instanceof Error ? err.message : 'Failed to create session'
      });
    } finally {
      setLoading(false);
    }
  }, [formData, validateForm, apiCall, onNotification, onRouteChange]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    onRouteChange('sessions');
  }, [onRouteChange]);

  return (
    <div className="user-content">
      <div className="user-page-header">
        <h1 className="user-page-title">Create New Session</h1>
        <p className="user-page-subtitle">Upload and secure your data in a new session</p>
      </div>

      <form onSubmit={handleSubmit} className="user-card">
        <div className="user-card-body">
          {/* Session Name */}
          <div className="user-form-group">
            <label className="user-form-label" htmlFor="session-name">
              Session Name *
            </label>
            <input
              type="text"
              id="session-name"
              className="user-form-input"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="Enter a name for your session"
              maxLength={100}
            />
            {validationErrors.name && (
              <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                {validationErrors.name}
              </div>
            )}
          </div>

          {/* Description */}
          <div className="user-form-group">
            <label className="user-form-label" htmlFor="session-description">
              Description
            </label>
            <textarea
              id="session-description"
              className="user-form-input user-form-textarea"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Optional description of your session"
              maxLength={500}
              rows={3}
            />
            {validationErrors.description && (
              <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                {validationErrors.description}
              </div>
            )}
          </div>

          {/* File Upload Area */}
          <div className="user-form-group">
            <label className="user-form-label">
              Session Data *
            </label>
            <div
              className={`user-file-upload-area ${dragOver ? 'drag-over' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              style={{
                border: '2px dashed var(--user-border-primary)',
                borderRadius: 'var(--user-radius-lg)',
                padding: '2rem',
                textAlign: 'center',
                backgroundColor: dragOver ? 'var(--user-bg-tertiary)' : 'var(--user-bg-primary)',
                transition: 'all var(--user-transition-fast)',
                cursor: 'pointer'
              }}
            >
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📁</div>
                <p style={{ margin: '0 0 0.5rem 0', fontWeight: '500' }}>
                  Drop your file here or click to browse
                </p>
                <p style={{ margin: '0', color: 'var(--user-text-secondary)', fontSize: '0.875rem' }}>
                  Maximum file size: 10MB
                </p>
              </div>
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".txt,.md,.json,.csv,.xml"
                style={{ display: 'none' }}
                id="file-upload"
              />
              <label htmlFor="file-upload" className="user-btn user-btn-secondary">
                Choose File
              </label>
            </div>

            {/* Data Preview */}
            {formData.data && (
              <div style={{ marginTop: '1rem' }}>
                <label className="user-form-label">Data Preview</label>
                <textarea
                  className="user-form-input user-form-textarea"
                  value={formData.data}
                  onChange={(e) => handleInputChange('data', e.target.value)}
                  rows={6}
                  placeholder="Enter your session data here or upload a file"
                />
                <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)', marginTop: '0.25rem' }}>
                  {formData.data.length} characters
                </div>
              </div>
            )}

            {validationErrors.data && (
              <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                {validationErrors.data}
              </div>
            )}
          </div>

          {/* Session Options */}
          <div className="user-form-group">
            <label className="user-form-label">Session Options</label>
            
            <div style={{ display: 'grid', gap: '1rem' }}>
              {/* Encryption */}
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={formData.encryption_enabled}
                  onChange={(e) => handleInputChange('encryption_enabled', e.target.checked)}
                />
                <span>Enable encryption for this session</span>
              </label>

              {/* Auto Anchor */}
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={formData.auto_anchor}
                  onChange={(e) => handleInputChange('auto_anchor', e.target.checked)}
                />
                <span>Automatically anchor to blockchain when complete</span>
              </label>

              {/* Chunk Size */}
              <div>
                <label className="user-form-label" htmlFor="chunk-size">
                  Chunk Size (bytes)
                </label>
                <select
                  id="chunk-size"
                  className="user-form-input user-form-select"
                  value={formData.chunk_size}
                  onChange={(e) => handleInputChange('chunk_size', parseInt(e.target.value))}
                >
                  <option value={512}>512 bytes</option>
                  <option value={1024}>1 KB</option>
                  <option value={2048}>2 KB</option>
                  <option value={4096}>4 KB</option>
                  <option value={8192}>8 KB</option>
                </select>
                {validationErrors.chunk_size && (
                  <div className="user-error-message" style={{ color: 'var(--user-error)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                    {validationErrors.chunk_size}
                  </div>
                )}
              </div>

              {/* Priority */}
              <div>
                <label className="user-form-label" htmlFor="priority">
                  Priority
                </label>
                <select
                  id="priority"
                  className="user-form-input user-form-select"
                  value={formData.priority}
                  onChange={(e) => handleInputChange('priority', e.target.value)}
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className="user-card-footer">
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="user-btn user-btn-secondary"
              onClick={handleCancel}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="user-btn user-btn-primary"
              disabled={loading}
            >
              {loading ? 'Creating Session...' : 'Create Session'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
