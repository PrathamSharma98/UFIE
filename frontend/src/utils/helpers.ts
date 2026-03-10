export const severityColor = (severity: string): string => {
  switch (severity) {
    case 'Critical': return '#dc2626';
    case 'High': return '#ea580c';
    case 'Moderate': return '#eab308';
    case 'Low': return '#22c55e';
    default: return '#3b82f6';
  }
};

export const categoryColor = (category: string): string => {
  switch (category) {
    case 'Critical Risk': return '#dc2626';
    case 'Moderate Risk': return '#ea580c';
    case 'Prepared': return '#eab308';
    case 'Resilient': return '#22c55e';
    default: return '#94a3b8';
  }
};

export const probabilityToColor = (p: number): string => {
  if (p >= 0.7) return '#dc2626';
  if (p >= 0.5) return '#ea580c';
  if (p >= 0.3) return '#eab308';
  return '#22c55e';
};

export const formatNumber = (n: number): string => {
  if (n >= 10000000) return (n / 10000000).toFixed(1) + ' Cr';
  if (n >= 100000) return (n / 100000).toFixed(1) + ' L';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toString();
};

export const formatPercent = (n: number): string => {
  return n.toFixed(1) + '%';
};

export const getReadinessEmoji = (score: number): string => {
  if (score >= 81) return '';
  if (score >= 61) return '';
  if (score >= 31) return '';
  return '';
};

export const monthName = (month: number): string => {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return months[month - 1] || '';
};
