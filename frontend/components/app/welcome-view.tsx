'use client';

import { useState } from 'react';
import { Button } from '@/components/livekit/button';

function ImprovBattleLogo() {
  return (
    <div className="mb-6 flex flex-col items-center">
      <div className="relative">
        <div className="absolute -inset-4 bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400 rounded-full blur-xl opacity-50 animate-pulse" />
        <svg
          width="80"
          height="80"
          viewBox="0 0 80 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="relative text-foreground"
        >
          <circle cx="40" cy="40" r="36" stroke="currentColor" strokeWidth="3" fill="none" />
          <path
            d="M25 50 L35 30 L40 45 L45 25 L55 50"
            stroke="url(#gradient)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
          <circle cx="25" cy="35" r="4" fill="currentColor" />
          <circle cx="55" cy="35" r="4" fill="currentColor" />
          <defs>
            <linearGradient id="gradient" x1="25" y1="25" x2="55" y2="50">
              <stop offset="0%" stopColor="#9333ea" />
              <stop offset="50%" stopColor="#ec4899" />
              <stop offset="100%" stopColor="#f97316" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <h1 className="mt-4 text-3xl font-bold bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400 bg-clip-text text-transparent">
        IMPROV BATTLE
      </h1>
      <p className="text-muted-foreground text-sm mt-1">Voice AI Game Show</p>
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: (playerName: string) => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [playerName, setPlayerName] = useState('');
  const [isHovering, setIsHovering] = useState(false);

  const handleStart = () => {
    const name = playerName.trim() || 'Player';
    onStartCall(name);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && playerName.trim()) {
      handleStart();
    }
  };

  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center px-4">
        <ImprovBattleLogo />

        <div className="max-w-md w-full space-y-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-foreground mb-4">
              Welcome, Contestant!
            </h2>
            <p className="text-muted-foreground text-sm mb-6">
              Get ready to showcase your improv skills! Our AI host will guide you through hilarious scenarios.
            </p>
            
            <div className="space-y-4">
              <div className="text-left">
                <label htmlFor="playerName" className="block text-sm font-medium text-foreground mb-2">
                  Your Stage Name
                </label>
                <input
                  type="text"
                  id="playerName"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter your name..."
                  className="w-full px-4 py-3 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                  maxLength={30}
                />
              </div>

              <Button
                variant="primary"
                size="lg"
                onClick={handleStart}
                onMouseEnter={() => setIsHovering(true)}
                onMouseLeave={() => setIsHovering(false)}
                className="w-full font-bold text-lg py-6 bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 transition-all duration-300 shadow-lg hover:shadow-purple-500/25"
              >
                {isHovering ? "Let's Go!" : startButtonText}
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-card/50 rounded-lg p-3 border border-border/50">
              <div className="text-2xl mb-1">🎭</div>
              <p className="text-xs text-muted-foreground">3-5 Rounds</p>
            </div>
            <div className="bg-card/50 rounded-lg p-3 border border-border/50">
              <div className="text-2xl mb-1">🎤</div>
              <p className="text-xs text-muted-foreground">Voice First</p>
            </div>
            <div className="bg-card/50 rounded-lg p-3 border border-border/50">
              <div className="text-2xl mb-1">🏆</div>
              <p className="text-xs text-muted-foreground">AI Host</p>
            </div>
          </div>
        </div>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Powered by{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://murf.ai"
            className="underline"
          >
            Murf Falcon
          </a>{' '}
          &{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://livekit.io"
            className="underline"
          >
            LiveKit
          </a>
        </p>
      </div>
    </div>
  );
};
