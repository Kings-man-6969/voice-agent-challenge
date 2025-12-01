'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import type { AppConfig } from '@/app-config';
import { ChatTranscript } from '@/components/app/chat-transcript';
import { PreConnectMessage } from '@/components/app/preconnect-message';
import { TileLayout } from '@/components/app/tile-layout';
import { GameScenario } from '@/components/app/game-scenario';
import {
  AgentControlBar,
  type ControlBarControls,
} from '@/components/livekit/agent-control-bar/agent-control-bar';
import { useChatMessages } from '@/hooks/useChatMessages';
import { useConnectionTimeout } from '@/hooks/useConnectionTimout';
import { useDebugMode } from '@/hooks/useDebug';
import { cn } from '@/lib/utils';
import { ScrollArea } from '../livekit/scroll-area/scroll-area';
import { useSession } from './session-provider';

const MotionBottom = motion.create('div');

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';
const BOTTOM_VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut' as const,
  },
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

function GameHeader({ playerName }: { playerName: string }) {
  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-b from-background via-background/95 to-transparent pb-8 pt-4">
      <div className="mx-auto max-w-2xl px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-purple-600 to-pink-500 rounded-full blur opacity-50" />
              <div className="relative bg-background rounded-full p-2">
                <span className="text-lg">🎭</span>
              </div>
            </div>
            <div>
              <h1 className="text-sm font-bold bg-gradient-to-r from-purple-600 to-pink-500 bg-clip-text text-transparent">
                IMPROV BATTLE
              </h1>
              <p className="text-xs text-muted-foreground">Live Game Show</p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm rounded-full px-3 py-1.5 border border-border/50">
            <span className="text-xs text-muted-foreground">Player:</span>
            <span className="text-sm font-semibold text-foreground">{playerName}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

interface SessionViewProps {
  appConfig: AppConfig;
}

export const SessionView = ({
  appConfig,
  ...props
}: React.ComponentProps<'section'> & SessionViewProps) => {
  useConnectionTimeout(200_000);
  useDebugMode({ enabled: IN_DEVELOPMENT });

  const { playerName } = useSession();
  const messages = useChatMessages();
  const [chatOpen, setChatOpen] = useState(false);
  const [currentRound, setCurrentRound] = useState(1);
  const [scenario, setScenario] = useState(
    'Get ready for your first improv challenge! Your AI host will guide you through hilarious scenarios.'
  );
  const [isRoundActive, setIsRoundActive] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Simulate game progression based on messages
  useEffect(() => {
    if (messages.length > 0) {
      setIsRoundActive(true);
      const roundNum = Math.min(1 + Math.floor(messages.length / 4), 5);
      setCurrentRound(roundNum);

      // Update scenario based on round
      const scenarios = [
        'You are a time traveler stranded in ancient Egypt. Convince the Pharaoh you\'re from the future!',
        'You\'re a detective investigating why all the pigeons in the city have disappeared.',
        'You must convince someone to buy an invisible sandwich for $1000.',
        'You\'re a yoga instructor teaching aliens how to meditate.',
        'The finale: You\'re a superhero with the lamest power imaginable – describe it!',
      ];
      setScenario(scenarios[roundNum - 1] || scenarios[4]);
    }
  }, [messages]);

  const controls: ControlBarControls = {
    leave: true,
    microphone: true,
    chat: appConfig.supportsChatInput,
    camera: appConfig.supportsVideoInput,
    screenShare: appConfig.supportsVideoInput,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section className="bg-background relative z-10 h-full w-full overflow-hidden" {...props}>
      <GameHeader playerName={playerName || 'Player'} />
      
      <div
        className={cn(
          'fixed inset-0 grid grid-cols-1 grid-rows-1',
          !chatOpen && 'pointer-events-none'
        )}
      >
        <Fade top className="absolute inset-x-4 top-0 h-40" />
        <ScrollArea ref={scrollAreaRef} className="px-4 pt-40 pb-[150px] md:px-6 md:pb-[180px]">
          <div className="mx-auto max-w-2xl space-y-6">
            {/* Game Scenario Card */}
            {!chatOpen && (
              <GameScenario
                round={currentRound}
                totalRounds={5}
                scenario={scenario}
                isActive={isRoundActive}
              />
            )}
            
            {/* Chat Transcript */}
            <ChatTranscript
              hidden={!chatOpen}
              messages={messages}
              className="space-y-3 transition-opacity duration-300 ease-out"
            />
          </div>
        </ScrollArea>
      </div>

      <TileLayout chatOpen={chatOpen} />

      <MotionBottom
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="fixed inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {appConfig.isPreConnectBufferEnabled && (
          <PreConnectMessage messages={messages} className="pb-4" />
        )}
        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar controls={controls} onChatOpenChange={setChatOpen} />
        </div>
      </MotionBottom>
    </section>
  );
};
