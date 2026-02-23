export function CertLogo({ className = "w-8 h-8" }: { className?: string }) {
    return (
        <svg
            viewBox="0 0 100 100"
            className={className}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <defs>
                <linearGradient id="certFinderGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#6366f1" />
                </linearGradient>
                <filter id="shieldGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="2" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
            </defs>

            {/* Background Glow Overlay */}
            <circle cx="50" cy="50" r="40" fill="url(#certFinderGradient)" opacity="0.15" className="animate-pulse" />

            {/* Shield Shape */}
            <path
                d="M50 12L22 25V50C22 66.5 34.5 81.5 50 86C65.5 81.5 78 66.5 78 50V25L50 12Z"
                fill="url(#certFinderGradient)"
                filter="url(#shieldGlow)"
                className="drop-shadow-[0_0_8px_rgba(59,130,246,0.3)]"
            />

            {/* Inner Shield (Darker Section) */}
            <path
                d="M50 18L28 28V48C28 61 38 73 50 77C62 73 72 61 72 48V28L50 18Z"
                fill="#0f172a"
                opacity="0.6"
            />

            {/* Checkmark */}
            <path
                d="M38 48L46 56L62 40"
                stroke="white"
                strokeWidth="7"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="drop-shadow-md"
            />

            {/* Magnifying Glass (Integrated bottom right) */}
            <g className="drop-shadow-lg">
                <circle cx="72" cy="72" r="14" fill="#0f172a" stroke="white" strokeWidth="3" />
                <circle cx="72" cy="72" r="8" stroke="url(#certFinderGradient)" strokeWidth="2" />
                <line x1="81" y1="81" x2="89" y2="89" stroke="white" strokeWidth="4" strokeLinecap="round" />
            </g>
        </svg>
    );
}
