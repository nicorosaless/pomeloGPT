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
                width: '20px',
                height: '20px',
                background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #3b82f6 100%)',
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
                    backgroundImage: 'linear-gradient(to right, #60a5fa, #c4b5fd, #60a5fa)',
                    backgroundSize: '200% auto',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    animation: 'shimmer 3s linear infinite',
                    letterSpacing: '0.05em'
                }}>
                    {progressMessage}
                </span>
            )}
        </div>
    );
};

export default LoadingOrb;
