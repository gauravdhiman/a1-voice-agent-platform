import { useState, useEffect } from 'react';

export function useLiveTime() {
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    // Update immediately
    setCurrentTime(Date.now());

    // Update every second
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return currentTime;
}

export function formatTimeUntilExpiry(expiresAt: number | null, currentTime: number) {
  if (!expiresAt) return null;

  const secondsLeft = Math.floor((expiresAt * 1000 - currentTime) / 1000);
  const minutesLeft = Math.floor(secondsLeft / 60);

  if (minutesLeft < 1) return secondsLeft > 0 ? "< 1 minute" : "Expired";
  if (minutesLeft < 60) return `${minutesLeft} minutes`;
  if (minutesLeft < 1440) return `${Math.floor(minutesLeft / 60)} hours`;
  return `${Math.floor(minutesLeft / 1440)} days`;
}