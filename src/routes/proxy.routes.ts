import { Router, Request, Response, NextFunction } from "express";
import http from "http";
import { createProxyMiddleware, fixRequestBody } from "http-proxy-middleware";
import { apiKeyGuard } from "../middlewares/apiKey.middleware";
import { dynamicRateLimit } from "../middlewares/rateLimit.middleware";
import {
  recordRpcMetrics,
  recordRateLimitHit,
} from "../services/metrics.service";
import { ProxyController, getRandomUrl } from "../controllers/proxy.controller";
import { config } from "../config";

const router = Router();
const proxyController = new ProxyController();

// Shared keep-alive agent for all upstream connections
const keepAliveAgent = new http.Agent({
  keepAlive: true,
  keepAliveMsecs: 30_000,
  maxSockets: 128,
  maxFreeSockets: 32,
});

// --- Proxy instance cache ---
// Key: `${targetUrl}:${chainName}:${endpointType}`
const proxyCache = new Map<string, ReturnType<typeof createProxyMiddleware>>();

const getOrCreateProxy = (
  targetUrl: string,
  chainName: string,
  endpointType: "execution" | "consensus"
) => {
  const cacheKey = `${targetUrl}:${chainName}:${endpointType}`;
  let proxy = proxyCache.get(cacheKey);
  if (proxy) return proxy;

  const pathRewriteRules: { [key: string]: string } = {};
  if (endpointType === "execution") {
    pathRewriteRules[`^/${chainName}/exec/[^/]+`] = "";
  } else {
    pathRewriteRules[`^/${chainName}/cons/[^/]+`] = "";
  }

  proxy = createProxyMiddleware({
    target: targetUrl,
    changeOrigin: true,
    timeout: 60000,
    proxyTimeout: 60000,
    pathRewrite: pathRewriteRules,
    agent: keepAliveAgent,
    onProxyReq: (proxyReq, req: any) => {
      fixRequestBody(proxyReq, req);
      req.startTime = Date.now();
    },
    onProxyRes: (proxyRes, req: any, res) => {
      const duration = (Date.now() - req.startTime) / 1000;
      const app = req.app;
      const apiKey = req.apiKey || "unknown";

      let rpcMethod = "unknown";
      if (req.body && req.body.method) {
        rpcMethod = req.body.method;
      }

      if (app) {
        recordRpcMetrics(
          app.userId.toString(),
          apiKey,
          rpcMethod,
          endpointType,
          duration
        );
      }

      res.setHeader("X-RPC-Gateway", "NodeBridge");
      res.setHeader("X-Endpoint-Type", `${chainName}-${endpointType}`);
      res.setHeader("X-Response-Time", `${duration}s`);
    },
    onError: (err, req: any, res) => {
      console.error(
        `[${chainName.toUpperCase()}-${endpointType.toUpperCase()}] Proxy Error:`,
        err.message
      );
      res.status(502).json({
        error: "Bad Gateway",
        message: `Failed to connect to the ${chainName} ${endpointType} node`,
        endpointType: `${chainName}-${endpointType}`,
      });
    },
  });

  proxyCache.set(cacheKey, proxy);
  return proxy;
};

// Rate limiting with metrics (simplified — no monkey-patching res.status)
const rateLimitWithMetrics = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const originalSend = res.status;
  res.status = function (statusCode: number) {
    if (statusCode === 429 && (req as any).app && (req as any).apiKey) {
      recordRateLimitHit(
        (req as any).app.userId.toString(),
        (req as any).apiKey
      );
    }
    return originalSend.call(this, statusCode);
  };

  return dynamicRateLimit(req as any, res, next);
};

// Execution layer proxy routes (JSON-RPC)
router.use(
  "/:chain/exec/:key",
  apiKeyGuard as any,
  rateLimitWithMetrics,
  (req: Request, res: Response, next: NextFunction) => {
    const chainName = req.params.chain.toLowerCase();
    const chainConfig = config.getChainConfig(chainName);

    if (
      !chainConfig?.executionRpcUrl ||
      chainConfig.executionRpcUrl.length === 0
    ) {
      return res.status(404).json({
        error: `Execution RPC URL not configured for chain ${chainName}`,
      });
    }

    const selectedUrl = getRandomUrl(chainConfig.executionRpcUrl);
    if (!selectedUrl) {
      return res.status(500).json({
        error: `Failed to select execution RPC URL for chain ${chainName}`,
      });
    }

    const proxy = getOrCreateProxy(selectedUrl, chainName, "execution");
    proxy(req, res, next);
  }
);

// Consensus layer proxy routes (REST API)
router.use(
  "/:chain/cons/:key",
  apiKeyGuard as any,
  rateLimitWithMetrics,
  (req: Request, res: Response, next: NextFunction) => {
    const chainName = req.params.chain.toLowerCase();
    const chainConfig = config.getChainConfig(chainName);

    if (
      !chainConfig?.consensusApiUrl ||
      chainConfig.consensusApiUrl.length === 0
    ) {
      return res.status(404).json({
        error: `Consensus API URL not configured for chain ${chainName}`,
      });
    }

    const selectedUrl = getRandomUrl(chainConfig.consensusApiUrl);
    if (!selectedUrl) {
      return res.status(500).json({
        error: `Failed to select consensus API URL for chain ${chainName}`,
      });
    }

    const proxy = getOrCreateProxy(selectedUrl, chainName, "consensus");
    proxy(req, res, next);
  }
);

// Health check endpoint for proxied services
router.get("/health/:chain", proxyController.checkProxyHealth);

export default router;
