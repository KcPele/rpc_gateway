import { Request, Response, NextFunction } from "express";
import App, { IApp } from "../models/app.model";

export type ApiKeyRequest = Request & {
  app?: IApp;
  apiKey?: string;
};

// --- In-memory API key cache ---
interface CachedApp {
  app: IApp;
  cachedAt: number;
}

const apiKeyCache = new Map<string, CachedApp>();
const CACHE_TTL_MS = 60_000; // 1 minute TTL

// --- Batched counter updates ---
interface PendingCounters {
  requests: number;
  dailyRequests: number;
  lastResetDate?: Date;
}

const pendingUpdates = new Map<string, PendingCounters>();
let flushTimer: NodeJS.Timeout | null = null;

function scheduleBatchFlush() {
  if (flushTimer) return;
  flushTimer = setTimeout(flushCounters, 5_000); // flush every 5s
}

async function flushCounters() {
  flushTimer = null;
  if (pendingUpdates.size === 0) return;

  const batch = new Map(pendingUpdates);
  pendingUpdates.clear();

  const ops = Array.from(batch.entries()).map(([apiKey, counters]) => {
    const update: any = {
      $inc: { requests: counters.requests, dailyRequests: counters.dailyRequests },
    };
    if (counters.lastResetDate) {
      update.$set = { lastResetDate: counters.lastResetDate };
    }
    return App.updateOne({ apiKey, isActive: true }, update).catch((err) => {
      console.error(`Failed to flush counters for key ${apiKey}:`, err.message);
    });
  });

  await Promise.all(ops);
}

// Flush on shutdown
process.on("SIGTERM", flushCounters);
process.on("SIGINT", flushCounters);

/** Invalidate cache for a specific key (call after regenerate, update, delete) */
export function invalidateApiKeyCache(apiKey: string) {
  apiKeyCache.delete(apiKey);
}

/** Clear entire cache */
export function clearApiKeyCache() {
  apiKeyCache.clear();
}

export const apiKeyGuard = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const key = (req as any).params?.key;
    const requestedChain = (req as any).params?.chain?.toLowerCase();

    if (!key) {
      return res.status(400).json({ error: "Missing API key in URL path" });
    }
    if (!requestedChain) {
      return res.status(400).json({ error: "Missing chain in URL path" });
    }

    // Check cache first
    const now = Date.now();
    let app: IApp | null = null;
    const cached = apiKeyCache.get(key);

    if (cached && now - cached.cachedAt < CACHE_TTL_MS) {
      app = cached.app;
    } else {
      // Cache miss or expired — query DB
      apiKeyCache.delete(key);
      app = await App.findOne({ apiKey: key, isActive: true }).lean<IApp>();
      if (app) {
        apiKeyCache.set(key, { app, cachedAt: now });
      }
    }

    if (!app) {
      return res.status(403).json({ error: "Invalid or inactive API key" });
    }

    // Check chain match
    if (app.chainName.toLowerCase() !== requestedChain) {
      return res.status(403).json({
        error: `API key is not valid for chain '${requestedChain}'`,
        expectedChain: app.chainName,
      });
    }

    // Check daily reset
    const today = new Date().toDateString();
    const lastReset = app.lastResetDate
      ? new Date(app.lastResetDate).toDateString()
      : null;
    const needsReset = lastReset !== today;

    // Queue counter increment (batched write)
    let pending = pendingUpdates.get(key);
    if (!pending) {
      pending = { requests: 0, dailyRequests: 0 };
      pendingUpdates.set(key, pending);
    }

    if (needsReset) {
      // Reset daily counter in batch
      pending.dailyRequests = 1 - (app.dailyRequests || 0); // net effect: set to 1
      pending.lastResetDate = new Date();
      pending.requests += 1;
    } else {
      pending.requests += 1;
      pending.dailyRequests += 1;
    }

    scheduleBatchFlush();

    // Compute effective daily count for limit check
    const effectiveDailyRequests = needsReset
      ? 1
      : app.dailyRequests + pending.dailyRequests;

    if (effectiveDailyRequests > app.dailyRequestsLimit) {
      return res.status(429).json({
        error: "Daily request limit exceeded for this app",
      });
    }

    // Attach to request
    (req as any).app = app;
    (req as any).apiKey = key;

    next();
  } catch (error) {
    console.error("API Key middleware error:", error);
    res.status(500).json({ error: "Internal server error in API key middleware" });
  }
};
