'use client';

import { createContext, useContext, useMemo, useState } from 'react';
import { RoomContext } from '@livekit/components-react';
import { APP_CONFIG_DEFAULTS, type AppConfig } from '@/app-config';
import { useRoom } from '@/hooks/useRoom';

const SessionContext = createContext<{
  appConfig: AppConfig;
  isSessionActive: boolean;
  playerName: string;
  startSession: (playerName: string) => void;
  endSession: () => void;
}>({
  appConfig: APP_CONFIG_DEFAULTS,
  isSessionActive: false,
  playerName: '',
  startSession: () => {},
  endSession: () => {},
});

interface SessionProviderProps {
  appConfig: AppConfig;
  children: React.ReactNode;
}

export const SessionProvider = ({ appConfig, children }: SessionProviderProps) => {
  const [playerName, setPlayerName] = useState('');
  const { room, isSessionActive, startSession: startRoomSession, endSession } = useRoom(appConfig);
  
  const startSession = (name: string) => {
    setPlayerName(name);
    startRoomSession(name);
  };

  const contextValue = useMemo(
    () => ({ appConfig, isSessionActive, playerName, startSession, endSession }),
    [appConfig, isSessionActive, playerName, startSession, endSession]
  );

  return (
    <RoomContext.Provider value={room}>
      <SessionContext.Provider value={contextValue}>{children}</SessionContext.Provider>
    </RoomContext.Provider>
  );
};

export function useSession() {
  return useContext(SessionContext);
}
