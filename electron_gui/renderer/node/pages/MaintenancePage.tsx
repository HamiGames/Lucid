import React, { useState, useEffect } from 'react';

// Types
interface MaintenanceTask {
  id: string;
  name: string;
  description: string;
  type: 'update' | 'backup' | 'cleanup' | 'optimization' | 'diagnostic';
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  estimated_duration: number; // in minutes
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress: number; // 0-100
  error_message?: string;
}

interface MaintenanceSchedule {
  id: string;
  task_name: string;
  task_type: MaintenanceTask['type'];
  schedule_type: 'once' | 'daily' | 'weekly' | 'monthly';
  schedule_time: string; // HH:MM format
  schedule_day?: number; // 1-7 for weekly, 1-31 for monthly
  is_active: boolean;
  last_run?: string;
  next_run?: string;
}

interface SystemDiagnostic {
  check_name: string;
  status: 'pass' | 'warning' | 'fail';
  message: string;
  recommendation?: string;
  details?: any;
}

interface MaintenancePageProps {
  nodeUser: any;
  systemHealth: any;
  onRouteChange: (route: string) => void;
  onNotification: (type: 'info' | 'warning' | 'error' | 'success', message: string) => void;
}

const MaintenancePage: React.FC<MaintenancePageProps> = ({
  nodeUser,
  systemHealth,
  onRouteChange,
  onNotification
}) => {
  const [maintenanceTasks, setMaintenanceTasks] = useState<MaintenanceTask[]>([]);
  const [scheduledTasks, setScheduledTasks] = useState<MaintenanceSchedule[]>([]);
  const [systemDiagnostics, setSystemDiagnostics] = useState<SystemDiagnostic[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'schedule' | 'diagnostics' | 'logs'>('tasks');
  const [selectedTask, setSelectedTask] = useState<MaintenanceTask | null>(null);

  useEffect(() => {
    loadMaintenanceData();
  }, []);

  const loadMaintenanceData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load maintenance tasks
      const tasksResponse = await fetch('/api/node/maintenance/tasks');
      if (tasksResponse.ok) {
        const tasksData = await tasksResponse.json();
        setMaintenanceTasks(tasksData);
      }

      // Load scheduled tasks
      const scheduleResponse = await fetch('/api/node/maintenance/schedule');
      if (scheduleResponse.ok) {
        const scheduleData = await scheduleResponse.json();
        setScheduledTasks(scheduleData);
      }

      // Load system diagnostics
      const diagnosticsResponse = await fetch('/api/node/maintenance/diagnostics');
      if (diagnosticsResponse.ok) {
        const diagnosticsData = await diagnosticsResponse.json();
        setSystemDiagnostics(diagnosticsData);
      }

      onNotification('success', 'Maintenance data loaded successfully');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load maintenance data';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const runMaintenanceTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/node/maintenance/tasks/${taskId}/run`, {
        method: 'POST',
      });

      if (response.ok) {
        onNotification('success', 'Maintenance task started');
        loadMaintenanceData(); // Refresh data
      } else {
        throw new Error('Failed to start maintenance task');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start maintenance task';
      onNotification('error', errorMessage);
    }
  };

  const cancelMaintenanceTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/node/maintenance/tasks/${taskId}/cancel`, {
        method: 'POST',
      });

      if (response.ok) {
        onNotification('success', 'Maintenance task cancelled');
        loadMaintenanceData(); // Refresh data
      } else {
        throw new Error('Failed to cancel maintenance task');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to cancel maintenance task';
      onNotification('error', errorMessage);
    }
  };

  const runSystemDiagnostics = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/node/maintenance/diagnostics/run', {
        method: 'POST',
      });

      if (response.ok) {
        const diagnosticsData = await response.json();
        setSystemDiagnostics(diagnosticsData);
        onNotification('success', 'System diagnostics completed');
      } else {
        throw new Error('Failed to run system diagnostics');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to run system diagnostics';
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const createScheduledTask = async (taskData: Partial<MaintenanceSchedule>) => {
    try {
      const response = await fetch('/api/node/maintenance/schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData),
      });

      if (response.ok) {
        onNotification('success', 'Scheduled task created');
        loadMaintenanceData(); // Refresh data
      } else {
        throw new Error('Failed to create scheduled task');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create scheduled task';
      onNotification('error', errorMessage);
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) {
      return `${minutes}m`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes}m`;
    }
  };

  const getTaskTypeIcon = (type: string): string => {
    const icons: Record<string, string> = {
      update: '📦',
      backup: '💾',
      cleanup: '🧹',
      optimization: '⚡',
      diagnostic: '🔍',
    };
    return icons[type] || '🔧';
  };

  const getTaskStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      pending: '#f39c12',
      running: '#3498db',
      completed: '#27ae60',
      failed: '#e74c3c',
    };
    return colors[status] || '#95a5a6';
  };

  const getPriorityColor = (priority: string): string => {
    const colors: Record<string, string> = {
      low: '#95a5a6',
      medium: '#f39c12',
      high: '#e67e22',
      critical: '#e74c3c',
    };
    return colors[priority] || '#95a5a6';
  };

  const getDiagnosticStatusIcon = (status: string): string => {
    const icons: Record<string, string> = {
      pass: '✅',
      warning: '⚠️',
      fail: '❌',
    };
    return icons[status] || '❓';
  };

  const renderMaintenanceTasks = () => {
    return (
      <div className="maintenance-tasks">
        <div className="section-header">
          <h3>Maintenance Tasks</h3>
          <button
            onClick={loadMaintenanceData}
            className="node-action-btn"
            title="Refresh Tasks"
          >
            🔄 Refresh
          </button>
        </div>
        
        <div className="tasks-grid">
          {maintenanceTasks.length > 0 ? (
            maintenanceTasks.map((task) => (
              <div key={task.id} className="task-card">
                <div className="task-header">
                  <div className="task-title">
                    <span className="task-icon">{getTaskTypeIcon(task.type)}</span>
                    <span className="task-name">{task.name}</span>
                  </div>
                  <div className="task-actions">
                    <span
                      className="task-status"
                      style={{ color: getTaskStatusColor(task.status) }}
                    >
                      {task.status}
                    </span>
                    <span
                      className="task-priority"
                      style={{ color: getPriorityColor(task.priority) }}
                    >
                      {task.priority}
                    </span>
                  </div>
                </div>
                
                <div className="task-body">
                  <p className="task-description">{task.description}</p>
                  
                  {task.status === 'running' && (
                    <div className="task-progress">
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${task.progress}%` }}
                        ></div>
                      </div>
                      <span className="progress-text">{task.progress}%</span>
                    </div>
                  )}
                  
                  <div className="task-meta">
                    <div className="task-meta-item">
                      <span className="meta-label">Duration:</span>
                      <span className="meta-value">{formatDuration(task.estimated_duration)}</span>
                    </div>
                    <div className="task-meta-item">
                      <span className="meta-label">Created:</span>
                      <span className="meta-value">{formatDate(task.created_at)}</span>
                    </div>
                    {task.started_at && (
                      <div className="task-meta-item">
                        <span className="meta-label">Started:</span>
                        <span className="meta-value">{formatDate(task.started_at)}</span>
                      </div>
                    )}
                    {task.completed_at && (
                      <div className="task-meta-item">
                        <span className="meta-label">Completed:</span>
                        <span className="meta-value">{formatDate(task.completed_at)}</span>
                      </div>
                    )}
                  </div>
                  
                  {task.error_message && (
                    <div className="task-error">
                      <span className="error-icon">❌</span>
                      <span className="error-message">{task.error_message}</span>
                    </div>
                  )}
                </div>
                
                <div className="task-footer">
                  {task.status === 'pending' && (
                    <button
                      onClick={() => runMaintenanceTask(task.id)}
                      className="node-action-btn"
                      title="Run Task"
                    >
                      ▶️ Run
                    </button>
                  )}
                  {task.status === 'running' && (
                    <button
                      onClick={() => cancelMaintenanceTask(task.id)}
                      className="node-action-btn danger"
                      title="Cancel Task"
                    >
                      ⏹️ Cancel
                    </button>
                  )}
                  <button
                    onClick={() => setSelectedTask(task)}
                    className="node-action-btn"
                    title="View Details"
                  >
                    📋 Details
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="no-tasks">
              <p>No maintenance tasks found.</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderScheduledTasks = () => {
    return (
      <div className="scheduled-tasks">
        <div className="section-header">
          <h3>Scheduled Tasks</h3>
          <button
            onClick={() => {/* Open create task modal */}}
            className="node-action-btn"
            title="Create Scheduled Task"
          >
            ➕ Create
          </button>
        </div>
        
        <div className="schedule-table">
          <div className="table-header">
            <div className="table-cell">Task Name</div>
            <div className="table-cell">Type</div>
            <div className="table-cell">Schedule</div>
            <div className="table-cell">Next Run</div>
            <div className="table-cell">Status</div>
            <div className="table-cell">Actions</div>
          </div>
          {scheduledTasks.length > 0 ? (
            scheduledTasks.map((schedule) => (
              <div key={schedule.id} className="table-row">
                <div className="table-cell">{schedule.task_name}</div>
                <div className="table-cell">
                  <span className="task-type">
                    {getTaskTypeIcon(schedule.task_type)} {schedule.task_type}
                  </span>
                </div>
                <div className="table-cell">
                  {schedule.schedule_type} at {schedule.schedule_time}
                </div>
                <div className="table-cell">
                  {schedule.next_run ? formatDate(schedule.next_run) : 'N/A'}
                </div>
                <div className="table-cell">
                  <span className={`status-badge ${schedule.is_active ? 'active' : 'inactive'}`}>
                    {schedule.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="table-cell">
                  <button className="node-action-btn small">Edit</button>
                  <button className="node-action-btn small danger">Delete</button>
                </div>
              </div>
            ))
          ) : (
            <div className="no-data">
              <p>No scheduled tasks found.</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderSystemDiagnostics = () => {
    return (
      <div className="system-diagnostics">
        <div className="section-header">
          <h3>System Diagnostics</h3>
          <button
            onClick={runSystemDiagnostics}
            className="node-action-btn"
            title="Run Diagnostics"
          >
            🔍 Run Diagnostics
          </button>
        </div>
        
        <div className="diagnostics-grid">
          {systemDiagnostics.length > 0 ? (
            systemDiagnostics.map((diagnostic, index) => (
              <div key={index} className="diagnostic-card">
                <div className="diagnostic-header">
                  <div className="diagnostic-title">
                    <span className="diagnostic-icon">
                      {getDiagnosticStatusIcon(diagnostic.status)}
                    </span>
                    <span className="diagnostic-name">{diagnostic.check_name}</span>
                  </div>
                  <span className={`diagnostic-status ${diagnostic.status}`}>
                    {diagnostic.status}
                  </span>
                </div>
                
                <div className="diagnostic-body">
                  <p className="diagnostic-message">{diagnostic.message}</p>
                  {diagnostic.recommendation && (
                    <div className="diagnostic-recommendation">
                      <strong>Recommendation:</strong> {diagnostic.recommendation}
                    </div>
                  )}
                  {diagnostic.details && (
                    <div className="diagnostic-details">
                      <details>
                        <summary>Details</summary>
                        <pre>{JSON.stringify(diagnostic.details, null, 2)}</pre>
                      </details>
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="no-diagnostics">
              <p>No diagnostic results available. Run diagnostics to check system health.</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderMaintenanceLogs = () => {
    return (
      <div className="maintenance-logs">
        <div className="section-header">
          <h3>Maintenance Logs</h3>
          <button
            onClick={loadMaintenanceData}
            className="node-action-btn"
            title="Refresh Logs"
          >
            🔄 Refresh
          </button>
        </div>
        
        <div className="logs-container">
          <div className="log-entry">
            <div className="log-header">
              <span className="log-timestamp">2024-01-15 14:30:25</span>
              <span className="log-level info">INFO</span>
            </div>
            <div className="log-message">
              System backup completed successfully. Backup size: 2.5 GB
            </div>
          </div>
          
          <div className="log-entry">
            <div className="log-header">
              <span className="log-timestamp">2024-01-15 12:15:10</span>
              <span className="log-level warning">WARN</span>
            </div>
            <div className="log-message">
              High disk usage detected: 85% of available space used
            </div>
          </div>
          
          <div className="log-entry">
            <div className="log-header">
              <span className="log-timestamp">2024-01-15 10:45:33</span>
              <span className="log-level success">SUCCESS</span>
            </div>
            <div className="log-message">
              Node optimization completed. Performance improved by 15%
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="maintenance-page">
        <div className="node-loading">
          <div className="spinner"></div>
          <span>Loading maintenance data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="maintenance-page">
        <div className="node-error">
          <h3>Maintenance Error</h3>
          <p>{error}</p>
          <button onClick={loadMaintenanceData} className="node-action-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="maintenance-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Node Maintenance</h1>
          <p className="page-subtitle">Manage maintenance tasks and system diagnostics</p>
        </div>
        <div className="page-actions">
          <button
            onClick={loadMaintenanceData}
            className="node-action-btn"
            title="Refresh Data"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="maintenance-tabs">
        <button
          className={`tab-button ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          Tasks
        </button>
        <button
          className={`tab-button ${activeTab === 'schedule' ? 'active' : ''}`}
          onClick={() => setActiveTab('schedule')}
        >
          Schedule
        </button>
        <button
          className={`tab-button ${activeTab === 'diagnostics' ? 'active' : ''}`}
          onClick={() => setActiveTab('diagnostics')}
        >
          Diagnostics
        </button>
        <button
          className={`tab-button ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          Logs
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'tasks' && renderMaintenanceTasks()}
        {activeTab === 'schedule' && renderScheduledTasks()}
        {activeTab === 'diagnostics' && renderSystemDiagnostics()}
        {activeTab === 'logs' && renderMaintenanceLogs()}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Task Details</h3>
              <button
                onClick={() => setSelectedTask(null)}
                className="modal-close"
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <div className="task-details">
                <div className="detail-item">
                  <strong>Name:</strong> {selectedTask.name}
                </div>
                <div className="detail-item">
                  <strong>Type:</strong> {selectedTask.type}
                </div>
                <div className="detail-item">
                  <strong>Status:</strong> {selectedTask.status}
                </div>
                <div className="detail-item">
                  <strong>Priority:</strong> {selectedTask.priority}
                </div>
                <div className="detail-item">
                  <strong>Description:</strong> {selectedTask.description}
                </div>
                <div className="detail-item">
                  <strong>Estimated Duration:</strong> {formatDuration(selectedTask.estimated_duration)}
                </div>
                <div className="detail-item">
                  <strong>Created:</strong> {formatDate(selectedTask.created_at)}
                </div>
                {selectedTask.error_message && (
                  <div className="detail-item">
                    <strong>Error:</strong> {selectedTask.error_message}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MaintenancePage;
