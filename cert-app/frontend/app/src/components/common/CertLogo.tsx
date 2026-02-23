export function CertLogo({ className = "w-8 h-8" }: { className?: string }) {
    return (
        <svg
            viewBox="0 0 100 100"
            className={className}
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
        >
            <defs>
                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
                <filter id="logoGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.5" />
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
            </defs>

            {/* Target/Focus Ring */}
            <circle cx="50" cy="50" r="45" stroke="url(#logoGradient)" strokeWidth="4" strokeDasharray="10 5" opacity="0.3" />

            {/* Main Shield Shape */}
            <path
                d="M50 15L20 28V52C20 68.5 32.5 83.5 50 88C67.5 83.5 80 68.5 80 52V28L50 15Z"
                fill="url(#logoGradient)"
                className="drop-shadow-lg"
            />

            {/* Checkmark inside shield */}
            <path
                d="M38 52L46 60L62 44"
                stroke="white"
                strokeWidth="6"
                strokeLinecap="round"
                strokeLinejoin="round"
            />

            {/* Search Ring integrated */}
            <circle cx="65" cy="65" r="12" stroke="white" strokeWidth="4" fill="#0f172a" />
            <line x1="74" y1="74" x2="82" y2="82" stroke="white" strokeWidth="4" strokeLinecap="round" />
        </svg>
    );
}
