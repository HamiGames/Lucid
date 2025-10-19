import React, { useState, useEffect } from 'react';
import { RequestBuilder } from '../components/RequestBuilder';
import { ResponseViewer } from '../components/ResponseViewer';

interface TestSuite {
  id: string;
  name: string;
  description: string;
  tests: TestCase[];
  createdAt: string;
  lastRun: string | null;
  status: 'pending' | 'running' | 'passed' | 'failed';
}

interface TestCase {
  id: string;
  name: string;
  description: string;
  request: {
    method: string;
    url: string;
    headers: Record<string, string>;
    body?: any;
    params?: Record<string, string>;
  };
  expectedResponse: {
    status: number;
    schema?: any;
  };
  assertions: TestAssertion[];
}

interface TestAssertion {
  id: string;
  type: 'status' | 'header' | 'body' | 'schema';
  property?: string;
  operator: 'equals' | 'contains' | 'matches' | 'exists';
  value: any;
}

interface TestResult {
  testId: string;
  passed: boolean;
  duration: number;
  actualResponse: any;
  assertions: Array<{
    assertionId: string;
    passed: boolean;
    message: string;
  }>;
  error?: string;
}

interface TestRun {
  id: string;
  suiteId: string;
  startedAt: string;
  completedAt: string | null;
  status: 'running' | 'completed' | 'failed';
  results: TestResult[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    duration: number;
  };
}

const TestingPage: React.FC = () => {
  const [testSuites, setTestSuites] = useState<TestSuite[]>([]);
  const [selectedSuite, setSelectedSuite] = useState<TestSuite | null>(null);
  const [currentTest, setCurrentTest] = useState<TestCase | null>(null);
  const [testRun, setTestRun] = useState<TestRun | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    loadTestSuites();
  }, []);

  const loadTestSuites = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load test suites from the system
      const suites = await loadTestSuitesFromSystem();
      setTestSuites(suites);
      
      if (suites.length > 0) {
        setSelectedSuite(suites[0]);
      }
    } catch (error) {
      console.error('Failed to load test suites:', error);
      setError('Failed to load test suites');
    } finally {
      setIsLoading(false);
    }
  };

  const loadTestSuitesFromSystem = async (): Promise<TestSuite[]> => {
    // Mock test suites - in real implementation, these would come from the testing service
    const mockSuites: TestSuite[] = [
      {
        id: 'auth-tests',
        name: 'Authentication Tests',
        description: 'Test suite for authentication endpoints',
        tests: [
          {
            id: 'login-test',
            name: 'User Login',
            description: 'Test user login with valid credentials',
            request: {
              method: 'POST',
              url: '/api/auth/login',
              headers: {
                'Content-Type': 'application/json'
              },
              body: {
                email: 'test@example.com',
                password: 'password123'
              }
            },
            expectedResponse: {
              status: 200
            },
            assertions: [
              {
                id: 'status-200',
                type: 'status',
                operator: 'equals',
                value: 200
              },
              {
                id: 'token-exists',
                type: 'body',
                property: 'token',
                operator: 'exists',
                value: true
              }
            ]
          },
          {
            id: 'login-invalid-test',
            name: 'Invalid Login',
            description: 'Test login with invalid credentials',
            request: {
              method: 'POST',
              url: '/api/auth/login',
              headers: {
                'Content-Type': 'application/json'
              },
              body: {
                email: 'test@example.com',
                password: 'wrongpassword'
              }
            },
            expectedResponse: {
              status: 401
            },
            assertions: [
              {
                id: 'status-401',
                type: 'status',
                operator: 'equals',
                value: 401
              }
            ]
          }
        ],
        createdAt: '2024-01-01T00:00:00Z',
        lastRun: null,
        status: 'pending'
      },
      {
        id: 'session-tests',
        name: 'Session Management Tests',
        description: 'Test suite for session management endpoints',
        tests: [
          {
            id: 'create-session-test',
            name: 'Create Session',
            description: 'Test creating a new session',
            request: {
              method: 'POST',
              url: '/api/sessions',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer <token>'
              },
              body: {
                data: 'test-data',
                metadata: {
                  description: 'Test session'
                }
              }
            },
            expectedResponse: {
              status: 201
            },
            assertions: [
              {
                id: 'status-201',
                type: 'status',
                operator: 'equals',
                value: 201
              },
              {
                id: 'session-id-exists',
                type: 'body',
                property: 'session_id',
                operator: 'exists',
                value: true
              }
            ]
          }
        ],
        createdAt: '2024-01-01T00:00:00Z',
        lastRun: null,
        status: 'pending'
      }
    ];

    return mockSuites;
  };

  const handleSuiteSelect = (suite: TestSuite) => {
    setSelectedSuite(suite);
    setCurrentTest(null);
    setTestRun(null);
  };

  const handleTestSelect = (test: TestCase) => {
    setCurrentTest(test);
  };

  const handleRunTest = async (test: TestCase) => {
    try {
      setIsRunning(true);
      setError(null);

      // Create test run
      const run: TestRun = {
        id: `run-${Date.now()}`,
        suiteId: selectedSuite!.id,
        startedAt: new Date().toISOString(),
        completedAt: null,
        status: 'running',
        results: [],
        summary: {
          total: 1,
          passed: 0,
          failed: 0,
          duration: 0
        }
      };

      setTestRun(run);

      // Execute the test
      const result = await executeTest(test);
      
      // Update test run
      const completedRun: TestRun = {
        ...run,
        completedAt: new Date().toISOString(),
        status: result.passed ? 'completed' : 'failed',
        results: [result],
        summary: {
          total: 1,
          passed: result.passed ? 1 : 0,
          failed: result.passed ? 0 : 1,
          duration: result.duration
        }
      };

      setTestRun(completedRun);
    } catch (error) {
      console.error('Test execution failed:', error);
      setError('Test execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  const handleRunSuite = async (suite: TestSuite) => {
    try {
      setIsRunning(true);
      setError(null);

      // Create test run for entire suite
      const run: TestRun = {
        id: `run-${Date.now()}`,
        suiteId: suite.id,
        startedAt: new Date().toISOString(),
        completedAt: null,
        status: 'running',
        results: [],
        summary: {
          total: suite.tests.length,
          passed: 0,
          failed: 0,
          duration: 0
        }
      };

      setTestRun(run);

      // Execute all tests in the suite
      const results: TestResult[] = [];
      let passed = 0;
      let failed = 0;
      const startTime = Date.now();

      for (const test of suite.tests) {
        try {
          const result = await executeTest(test);
          results.push(result);
          if (result.passed) {
            passed++;
          } else {
            failed++;
          }
        } catch (error) {
          results.push({
            testId: test.id,
            passed: false,
            duration: 0,
            actualResponse: null,
            assertions: [],
            error: error instanceof Error ? error.message : 'Unknown error'
          });
          failed++;
        }
      }

      const duration = Date.now() - startTime;

      // Update test run
      const completedRun: TestRun = {
        ...run,
        completedAt: new Date().toISOString(),
        status: failed === 0 ? 'completed' : 'failed',
        results,
        summary: {
          total: suite.tests.length,
          passed,
          failed,
          duration
        }
      };

      setTestRun(completedRun);
    } catch (error) {
      console.error('Test suite execution failed:', error);
      setError('Test suite execution failed');
    } finally {
      setIsRunning(false);
    }
  };

  const executeTest = async (test: TestCase): Promise<TestResult> => {
    const startTime = Date.now();
    
    try {
      // Mock test execution - in real implementation, this would make actual API calls
      const mockResponse = {
        status: test.expectedResponse.status,
        headers: { 'content-type': 'application/json' },
        data: { success: true, message: 'Test passed' }
      };

      const duration = Date.now() - startTime;

      // Run assertions
      const assertionResults = test.assertions.map(assertion => {
        let passed = false;
        let message = '';

        switch (assertion.type) {
          case 'status':
            passed = mockResponse.status === assertion.value;
            message = `Expected status ${assertion.value}, got ${mockResponse.status}`;
            break;
          case 'body':
            if (assertion.operator === 'exists') {
              passed = assertion.property ? mockResponse.data[assertion.property] !== undefined : true;
              message = `Property ${assertion.property} ${passed ? 'exists' : 'does not exist'}`;
            }
            break;
          default:
            passed = true;
            message = 'Assertion passed';
        }

        return {
          assertionId: assertion.id,
          passed,
          message
        };
      });

      const allAssertionsPassed = assertionResults.every(r => r.passed);

      return {
        testId: test.id,
        passed: allAssertionsPassed,
        duration,
        actualResponse: mockResponse,
        assertions: assertionResults
      };
    } catch (error) {
      return {
        testId: test.id,
        passed: false,
        duration: Date.now() - startTime,
        actualResponse: null,
        assertions: [],
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  };

  const handleCreateTestSuite = () => {
    // TODO: Implement test suite creation
    console.log('Create test suite');
  };

  const handleExportResults = () => {
    if (!testRun) return;

    try {
      const resultsData = JSON.stringify(testRun, null, 2);
      const blob = new Blob([resultsData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `test-results-${testRun.id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export results:', error);
      setError('Failed to export results');
    }
  };

  return (
    <div className="developer-content">
      <div className="developer-card">
        <div className="developer-card-header">
          <div>
            <h2 className="developer-card-title">API Testing</h2>
            <p className="developer-card-subtitle">
              Test API endpoints and validate responses
            </p>
          </div>
          <div className="developer-card-actions">
            <button 
              className="developer-btn developer-btn-primary"
              onClick={handleCreateTestSuite}
            >
              New Test Suite
            </button>
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={loadTestSuites}
              disabled={isLoading}
            >
              Refresh
            </button>
            {testRun && (
              <button 
                className="developer-btn developer-btn-secondary"
                onClick={handleExportResults}
              >
                Export Results
              </button>
            )}
          </div>
        </div>

        {isLoading && (
          <div className="developer-loading">
            <div className="developer-loading-spinner"></div>
            <p>Loading test suites...</p>
          </div>
        )}

        {error && (
          <div className="developer-error">
            <div className="developer-error-icon">⚠️</div>
            <div className="developer-error-title">Error</div>
            <div className="developer-error-message">{error}</div>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={loadTestSuites}
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '2rem' }}>
            <div>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Test Suites</h3>
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {testSuites.map(suite => (
                  <div
                    key={suite.id}
                    className={`developer-card ${selectedSuite?.id === suite.id ? 'active' : ''}`}
                    style={{ 
                      padding: '1rem', 
                      marginBottom: '0.5rem',
                      cursor: 'pointer',
                      border: selectedSuite?.id === suite.id ? '2px solid #3b82f6' : '1px solid rgba(51, 65, 85, 0.3)'
                    }}
                    onClick={() => handleSuiteSelect(suite)}
                  >
                    <h4 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>{suite.name}</h4>
                    <p style={{ margin: '0 0 0.5rem 0', color: '#94a3b8', fontSize: '0.875rem' }}>
                      {suite.description}
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {suite.tests.length} tests
                      </span>
                      <button
                        className="developer-btn developer-btn-primary"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRunSuite(suite);
                        }}
                        disabled={isRunning}
                      >
                        Run Suite
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              {selectedSuite && (
                <>
                  <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Tests</h3>
                  <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                    {selectedSuite.tests.map(test => (
                      <div
                        key={test.id}
                        className={`developer-card ${currentTest?.id === test.id ? 'active' : ''}`}
                        style={{ 
                          padding: '1rem', 
                          marginBottom: '0.5rem',
                          cursor: 'pointer',
                          border: currentTest?.id === test.id ? '2px solid #3b82f6' : '1px solid rgba(51, 65, 85, 0.3)'
                        }}
                        onClick={() => handleTestSelect(test)}
                      >
                        <h4 style={{ margin: '0 0 0.5rem 0', color: '#f8fafc' }}>{test.name}</h4>
                        <p style={{ margin: '0 0 0.5rem 0', color: '#94a3b8', fontSize: '0.875rem' }}>
                          {test.description}
                        </p>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {test.request.method} {test.request.url}
                          </span>
                          <button
                            className="developer-btn developer-btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRunTest(test);
                            }}
                            disabled={isRunning}
                          >
                            Run Test
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div>
              {testRun && (
                <>
                  <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Test Results</h3>
                  <div className="developer-card">
                    <div className="developer-card-header">
                      <div>
                        <h4 className="developer-card-title">Run Summary</h4>
                        <p className="developer-card-subtitle">
                          {testRun.summary.passed} passed, {testRun.summary.failed} failed
                        </p>
                      </div>
                    </div>
                    <div style={{ marginBottom: '1rem' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#10b981' }}>
                            {testRun.summary.passed}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Passed</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#ef4444' }}>
                            {testRun.summary.failed}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Failed</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#f8fafc' }}>
                            {testRun.summary.duration}ms
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Duration</div>
                        </div>
                      </div>
                    </div>
                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                      {testRun.results.map(result => (
                        <div
                          key={result.testId}
                          style={{
                            padding: '0.75rem',
                            border: '1px solid rgba(51, 65, 85, 0.3)',
                            borderRadius: '0.5rem',
                            marginBottom: '0.5rem',
                            background: result.passed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: '500', color: '#f8fafc' }}>
                              {result.testId}
                            </span>
                            <span style={{ 
                              color: result.passed ? '#10b981' : '#ef4444',
                              fontSize: '0.75rem'
                            }}>
                              {result.passed ? '✓ Passed' : '✗ Failed'}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                            {result.duration}ms
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export { TestingPage };
