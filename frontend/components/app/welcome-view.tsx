import { Button } from '@/components/livekit/button';
import { ShieldAlert } from 'lucide-react';

function BankLogo() {
  return (
    <div className="flex flex-col items-center mb-8">
      <img src="/icici-logo.png" alt="ICICI Bank Logo" className="h-16 mb-4" />
      <div className="flex items-center gap-2 mt-2 text-[#F37E20]">
        <ShieldAlert className="w-5 h-5" />
        <span className="font-semibold uppercase tracking-wider text-sm">Fraud Department</span>
      </div>
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center p-8 border rounded-xl shadow-lg max-w-md mx-auto">
        <BankLogo />

        <p className="text-foreground max-w-prose pt-4 leading-6 font-medium">
          We have detected unusual activity on your account.
        </p>
        <p className="text-muted-foreground text-sm mt-2 mb-6">
          Please speak with our automated fraud specialist to verify your recent transactions.
        </p>

        <Button
          variant="primary"
          size="lg"
          onClick={onStartCall}
          className="w-full font-semibold bg-[#F37E20] hover:bg-[#d66a15] text-white"
        >
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Secure Connection | 256-bit Encryption
        </p>
      </div>
    </div>
  );
};
