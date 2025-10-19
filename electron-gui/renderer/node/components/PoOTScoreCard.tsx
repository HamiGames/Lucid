import React, { useState, useEffect, useRef } from 'react';

// Types
interface PoOTScoreCardProps {
  pootScore: number;
  uptime: number;
  lastActivity: string;
  className?: string;
}

const PoOTScoreCard: React.FC<PoOTScoreCardProps> = ({
  pootScore,
  uptime,
  lastActivity,
  className = ''
}) => {
  const [scoreHistory, setScoreHistory] = useState<number[]>([]);
  const [scoreBreakdown, setScoreBreakdown] = useState({
    uptime: 0,
    performance: 0,
    reliability: 0,
    participation: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    loadPoOTScoreData();
  }, [pootScore]);

  useEffect(() => {
    if (canvasRef.current) {
      drawScoreChart();
    }
  }, [scoreHistory, pootScore]);

  const loadPoOTScoreData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/node/poot-score');
      if (response.ok) {
        const data = await response.json();
        setScoreHistory(data.history || []);
        setScoreBreakdown(data.breakdown || {
          uptime: 0,
          performance: 0,
          reliability: 0,
          participation: 0,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load PoOT score data');
    } finally {
      setIsLoading(false);
    }
  };

  const drawScoreChart = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    // Draw circular gauge
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    // Draw background circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#ecf0f1';
    ctx.lineWidth = 15;
    ctx.stroke();

    // Draw score arc
    const scoreAngle = (pootScore / 100) * 2 * Math.PI;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + scoreAngle);
    ctx.strokeStyle = getScoreColor(pootScore);
    ctx.lineWidth = 15;
    ctx.stroke();

    // Draw score text
    ctx.fillStyle = '#2c3e50';
    ctx.font = 'bold 28px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(pootScore.toFixed(1), centerX, centerY + 10);

    // Draw "PoOT Score" label
    ctx.font = '14px Inter';
    ctx.fillStyle = '#7f8c8d';
    ctx.fillText('PoOT Score', centerX, centerY + 35);
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return '#27ae60'; // Green
    if (score >= 60) return '#f39c12'; // Orange
    if (score >= 40) return '#e67e22'; // Dark Orange
    return '#e74c3c'; // Red
  };

  const getScoreGrade = (score: number): string => {
    if (score >= 90) return 'A+';
    if (score >= 80) return 'A';
    if (score >= 70) return 'B+';
    if (score >= 60) return 'B';
    if (score >= 50) return 'C+';
    if (score >= 40) return 'C';
    if (score >= 30) return 'D+';
    if (score >= 20) return 'D';
    return 'F';
  };

  const getScoreDescription = (score: number): string => {
    if (score >= 90) return 'Excellent performance';
    if (score >= 80) return 'Very good performance';
    if (score >= 70) return 'Good performance';
    if (score >= 60) return 'Average performance';
    if (score >= 50) return 'Below average performance';
    if (score >= 40) return 'Poor performance';
    if (score >= 30) return 'Very poor performance';
    if (score >= 20) return 'Critical performance';
    return 'Failing performance';
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

  const calculateScoreTrend = (): 'up' | 'down' | 'stable' => {
    if (scoreHistory.length < 2) return 'stable';
    
    const recent = scoreHistory.slice(-5);
    const older = scoreHistory.slice(-10, -5);
    
    if (recent.length === 0 || older.length === 0) return 'stable';
    
    const recentAvg = recent.reduce((sum, score) => sum + score, 0) / recent.length;
    const olderAvg = older.reduce((sum, score) => sum + score, 0) / older.length;
    
    const difference = recentAvg - olderAvg;
    
    if (difference > 2) return 'up';
    if (difference < -2) return 'down';
    return 'stable';
  };

  const getTrendIcon = (trend: 'up' | 'down' | 'stable'): string => {
    const icons: Record<string, string> = {
      up: '📈',
      down: '📉',
      stable: '➡️',
    };
    return icons[trend] || '➡️';
  };

  const getTrendColor = (trend: 'up' | 'down' | 'stable'): string => {
    const colors: Record<string, string> = {
      up: '#27ae60',
      down: '#e74c3c',
      stable: '#f39c12',
    };
    return colors[trend] || '#f39c12';
  };

  if (isLoading) {
    return (
      <div className={`poot-score-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">PoOT Score</h3>
        </div>
        <div className="card-body">
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading PoOT score...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`poot-score-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">PoOT Score</h3>
        </div>
        <div className="card-body">
          <div className="error-state">
            <span className="error-icon">❌</span>
            <span className="error-message">{error}</span>
            <button onClick={loadPoOTScoreData} className="retry-btn">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const trend = calculateScoreTrend();

  return (
    <div className={`poot-score-card ${className}`}>
      <div className="card-header">
        <h3 className="card-title">PoOT Score</h3>
        <div className="score-trend">
          <span className="trend-icon">{getTrendIcon(trend)}</span>
          <span
            className="trend-text"
            style={{ color: getTrendColor(trend) }}
          >
            {trend}
          </span>
        </div>
      </div>

      <div className="card-body">
        {/* Score Display */}
        <div className="score-display">
          <div className="score-chart">
            <canvas
              ref={canvasRef}
              width={200}
              height={200}
              className="score-canvas"
            />
          </div>
          <div className="score-info">
            <div className="score-grade">{getScoreGrade(pootScore)}</div>
            <div className="score-description">{getScoreDescription(pootScore)}</div>
          </div>
        </div>

        {/* Score Breakdown */}
        <div className="score-breakdown">
          <h4 className="breakdown-title">Score Breakdown</h4>
          <div className="breakdown-items">
            <div className="breakdown-item">
              <div className="breakdown-label">Uptime</div>
              <div className="breakdown-value">{scoreBreakdown.uptime.toFixed(1)}</div>
              <div className="breakdown-bar">
                <div
                  className="breakdown-fill"
                  style={{
                    width: `${scoreBreakdown.uptime}%`,
                    backgroundColor: getScoreColor(scoreBreakdown.uptime),
                  }}
                ></div>
              </div>
            </div>
            <div className="breakdown-item">
              <div className="breakdown-label">Performance</div>
              <div className="breakdown-value">{scoreBreakdown.performance.toFixed(1)}</div>
              <div className="breakdown-bar">
                <div
                  className="breakdown-fill"
                  style={{
                    width: `${scoreBreakdown.performance}%`,
                    backgroundColor: getScoreColor(scoreBreakdown.performance),
                  }}
                ></div>
              </div>
            </div>
            <div className="breakdown-item">
              <div className="breakdown-label">Reliability</div>
              <div className="breakdown-value">{scoreBreakdown.reliability.toFixed(1)}</div>
              <div className="breakdown-bar">
                <div
                  className="breakdown-fill"
                  style={{
                    width: `${scoreBreakdown.reliability}%`,
                    backgroundColor: getScoreColor(scoreBreakdown.reliability),
                  }}
                ></div>
              </div>
            </div>
            <div className="breakdown-item">
              <div className="breakdown-label">Participation</div>
              <div className="breakdown-value">{scoreBreakdown.participation.toFixed(1)}</div>
              <div className="breakdown-bar">
                <div
                  className="breakdown-fill"
                  style={{
                    width: `${scoreBreakdown.participation}%`,
                    backgroundColor: getScoreColor(scoreBreakdown.participation),
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Node Metrics */}
        <div className="node-metrics">
          <h4 className="metrics-title">Node Metrics</h4>
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-icon">⏱️</div>
              <div className="metric-content">
                <div className="metric-label">Uptime</div>
                <div className="metric-value">{uptime.toFixed(1)}%</div>
              </div>
            </div>
            <div className="metric-item">
              <div className="metric-icon">🕒</div>
              <div className="metric-content">
                <div className="metric-label">Last Activity</div>
                <div className="metric-value">{formatDate(lastActivity)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Score History */}
        {scoreHistory.length > 0 && (
          <div className="score-history">
            <h4 className="history-title">Recent Score History</h4>
            <div className="history-chart">
              <div className="history-bars">
                {scoreHistory.slice(-7).map((score, index) => (
                  <div key={index} className="history-bar">
                    <div
                      className="history-bar-fill"
                      style={{
                        height: `${score}%`,
                        backgroundColor: getScoreColor(score),
                      }}
                      title={`Score: ${score.toFixed(1)}`}
                    ></div>
                  </div>
                ))}
              </div>
              <div className="history-labels">
                {scoreHistory.slice(-7).map((score, index) => (
                  <div key={index} className="history-label">
                    {score.toFixed(0)}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Score Tips */}
        <div className="score-tips">
          <h4 className="tips-title">Improve Your Score</h4>
          <div className="tips-list">
            {pootScore < 80 && (
              <div className="tip-item">
                <span className="tip-icon">💡</span>
                <span className="tip-text">Maintain higher uptime to improve your score</span>
              </div>
            )}
            {scoreBreakdown.performance < 70 && (
              <div className="tip-item">
                <span className="tip-icon">⚡</span>
                <span className="tip-text">Optimize your node's performance and response times</span>
              </div>
            )}
            {scoreBreakdown.reliability < 70 && (
              <div className="tip-item">
                <span className="tip-icon">🛡️</span>
                <span className="tip-text">Ensure stable network connection and hardware</span>
              </div>
            )}
            {scoreBreakdown.participation < 70 && (
              <div className="tip-item">
                <span className="tip-icon">🤝</span>
                <span className="tip-text">Participate more actively in the network</span>
              </div>
            )}
            {pootScore >= 80 && (
              <div className="tip-item">
                <span className="tip-icon">🎉</span>
                <span className="tip-text">Great job! Your node is performing excellently</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export { PoOTScoreCard };
