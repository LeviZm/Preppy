import { useEffect, useState } from "react";
import { Users, Plus, LogOut, Crown } from "lucide-react";
import {
  getMyHouseholds,
  createHousehold,
  getHouseholdMembers,
  inviteMember,
  removeMember,
  type Household,
  type HouseholdMember,
} from "../api/households";
import { useAuth } from "../context/AuthContext";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";

type Status = "idle" | "submitting" | "error";

export function SettingsPage() {
  const { user } = useAuth();
  const [households, setHouseholds] = useState<Household[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setHouseholds(await getMyHouseholds());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load households.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-8 max-w-lg">
      <div>
        <h1 className="font-display text-2xl font-semibold text-stone-800">Settings</h1>
        {user && (
          <p className="text-sm text-stone-500 mt-1">
            Signed in as <span className="font-medium text-stone-700">{user.email}</span>
          </p>
        )}
      </div>

      <section>
        <h2 className="font-medium text-stone-700 mb-4 flex items-center gap-2">
          <Users size={16} aria-hidden="true" />
          Households
        </h2>

        {loading && (
          <div className="flex justify-center py-8"><Spinner /></div>
        )}

        {error && !loading && (
          <div role="alert" className="rounded-xl border border-clay-400/30 bg-clay-400/10 p-3 mb-4">
            <p className="text-sm text-clay-600">{error}</p>
            <button onClick={load} className="text-sm text-clay-600 underline underline-offset-2 mt-1">
              Try again
            </button>
          </div>
        )}

        {!loading && !error && households.length === 0 && (
          <p className="text-sm text-stone-400 mb-4">
            You are not part of any household yet. Create one to share meal planning with your partner.
          </p>
        )}

        {!loading && !error && households.map((h) => (
          <HouseholdCard key={h.id} household={h} currentUserId={user?.id} onChanged={load} />
        ))}

        <CreateHouseholdForm onCreated={load} />
      </section>
    </div>
  );
}

function HouseholdCard({
  household,
  currentUserId,
  onChanged,
}: {
  household: Household;
  currentUserId?: number;
  onChanged: () => void;
}) {
  const [members, setMembers] = useState<HouseholdMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  useEffect(() => {
    setLoadingMembers(true);
    getHouseholdMembers(household.id)
      .then(setMembers)
      .finally(() => setLoadingMembers(false));
  }, [household.id]);

  async function handleLeave(memberId: number) {
    if (!currentUserId) return;
    await removeMember(household.id, memberId);
    onChanged();
  }

  return (
    <Card className="p-4 mb-4">
      <h3 className="font-semibold text-stone-800 mb-3">{household.name}</h3>

      {loadingMembers ? (
        <div className="flex justify-center py-3"><Spinner size="sm" /></div>
      ) : (
        <ul className="space-y-2 mb-4">
          {members.map((m) => (
            <li key={m.id} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                {m.role === "admin" && (
                  <Crown size={12} className="text-sage-600 shrink-0" aria-label="Admin" />
                )}
                <span className="text-stone-700">{m.user.username}</span>
                <span className="text-stone-400 text-xs">{m.user.email}</span>
              </div>
              {m.user.id === currentUserId && (
                <button
                  onClick={() => handleLeave(m.user.id)}
                  className="flex items-center gap-1 text-xs text-stone-400 hover:text-clay-500 transition-colors"
                >
                  <LogOut size={12} aria-hidden="true" />
                  Leave
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <InviteForm householdId={household.id} onInvited={() => {
        getHouseholdMembers(household.id).then(setMembers);
      }} />
    </Card>
  );
}

function InviteForm({ householdId, onInvited }: { householdId: number; onInvited: () => void }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "submitting") return;
    if (!email.trim()) {
      setStatus("error");
      setErrorMessage("Email is required.");
      return;
    }
    setStatus("submitting");
    setErrorMessage(null);
    try {
      await inviteMember(householdId, email.trim());
      setEmail("");
      setStatus("idle");
      onInvited();
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Failed to invite. Please try again.");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-end border-t border-stone-100 pt-3">
      {status === "error" && errorMessage && (
        <p role="alert" className="text-xs text-clay-500 w-full mb-1">{errorMessage}</p>
      )}
      <div className="flex-1">
        <Input
          id={`invite-${householdId}`}
          name="email"
          label="Invite by email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="partner@example.com"
          disabled={isSubmitting}
        />
      </div>
      <Button type="submit" loading={isSubmitting} icon={<Plus size={14} />}>
        {isSubmitting ? "Inviting…" : "Invite"}
      </Button>
    </form>
  );
}

const EMPTY_HOUSEHOLD = { name: "" };

function CreateHouseholdForm({ onCreated }: { onCreated: () => void }) {
  const [fields, setFields] = useState(EMPTY_HOUSEHOLD);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "submitting") return;
    if (!fields.name.trim()) {
      setStatus("error");
      setErrorMessage("Household name is required.");
      return;
    }
    setStatus("submitting");
    setErrorMessage(null);
    try {
      await createHousehold(fields.name.trim());
      setFields(EMPTY_HOUSEHOLD);
      setStatus("idle");
      onCreated();
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Failed to create household.");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-end mt-2">
      {status === "error" && errorMessage && (
        <p role="alert" className="text-xs text-clay-500 w-full mb-1">{errorMessage}</p>
      )}
      <div className="flex-1">
        <Input
          id="new-household"
          name="name"
          label="New household name"
          value={fields.name}
          onChange={(e) => setFields({ name: e.target.value })}
          placeholder="The Melas"
          disabled={isSubmitting}
        />
      </div>
      <Button type="submit" loading={isSubmitting} icon={<Plus size={14} />}>
        {isSubmitting ? "Creating…" : "Create"}
      </Button>
    </form>
  );
}
