import React, { useEffect, useState } from 'react';

const LoadingOrb = ({ showProgress = false, progressMessage = '' }) => {
    const [isCircle, setIsCircle] = useState(true);

    useEffect(() => {
        const interval = setInterval(() => {
            setIsCircle(prev => !prev);
        }, 1500); // Toggle between circle and square every 1.5s

        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 0' }}>
            {/* Animated Orb - alternates between circle and rounded square */}
            <div style={{
                width: '16px',
                height: '16px',
                background: 'var(--primary-gradient)',
                backgroundSize: '200% 200%',
                animation: 'gradientShift 3s ease infinite',
                borderRadius: isCircle ? '50%' : '30%',
                transition: 'border-radius 1s ease-in-out'
            }} />

            {/* Progress Message (only shown during web search) */}
            {showProgress && progressMessage && (
                <span style={{
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    color: 'transparent',
                    backgroundImage: 'var(--loading-text-gradient)',
                    backgroundSize: '200% auto',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    animation: 'shimmer 3s linear infinite',
                    letterSpacing: '0.05em',
                    fontFamily: 'Inter, sans-serif'
                }}>
                    {progressMessage}
                </span>
            )}
        </div>
    );
};

export default LoadingOrb;
