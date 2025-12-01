'use client';

import { motion } from 'motion/react';
import { cn } from '@/lib/utils';

const MotionDiv = motion.create('div');

interface GameScenarioProps {
  round?: number;
  totalRounds?: number;
  scenario?: string;
  isActive?: boolean;
}

export function GameScenario({
  round = 1,
  totalRounds = 5,
  scenario = 'Get ready for your first improv challenge!',
  isActive = false,
}: GameScenarioProps) {
  const progress = (round / totalRounds) * 100;

  return (
    <MotionDiv
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="pointer-events-auto"
    >
      <div className="mx-auto max-w-2xl space-y-4 rounded-lg bg-card/80 backdrop-blur-sm border border-border/50 p-4">
        {/* Round Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-foreground">
              Round {round} of {totalRounds}
            </span>
            <span className="text-xs text-muted-foreground">
              {Math.round(progress)}%
            </span>
          </div>
          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-purple-600 to-pink-500"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
        </div>

        {/* Scenario Card */}
        <div
          className={cn(
            'rounded-md p-3 transition-all duration-300',
            isActive
              ? 'bg-gradient-to-r from-purple-600/20 to-pink-500/20 border border-purple-500/30'
              : 'bg-muted/40'
          )}
        >
          <div className="flex items-start gap-2">
            <span className="mt-0.5 text-lg">🎬</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
                Scenario
              </p>
              <p
                className={cn(
                  'text-sm leading-relaxed break-words',
                  isActive ? 'text-foreground font-medium' : 'text-muted-foreground'
                )}
              >
                {scenario}
              </p>
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center justify-between">
          <div
            className={cn(
              'flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium',
              isActive
                ? 'bg-gradient-to-r from-purple-600/30 to-pink-500/30 text-foreground'
                : 'bg-muted text-muted-foreground'
            )}
          >
            <span
              className={cn(
                'w-2 h-2 rounded-full animate-pulse',
                isActive ? 'bg-green-500' : 'bg-muted-foreground'
              )}
            />
            {isActive ? 'Your Turn' : 'Get Ready'}
          </div>
          <span className="text-xs text-muted-foreground">
            🎭 Improv Battle
          </span>
        </div>
      </div>
    </MotionDiv>
  );
}
