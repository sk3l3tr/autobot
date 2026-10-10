import Echo from "laravel-echo";
import client from "socket.io-client";

import { RequestReceived } from "./request-received.interface";
import { logger } from "./logger";

import net from "net";

const args = process.argv.slice(2);
const parsed: Record<string, string> = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace(/^--/, "");
  const value = args[i + 1];
  parsed[key] = value;
}

const apiKey = parsed["api-key"];
const tokenId = parsed["token-id"];
const socketHost = parsed["socket-host"] || "127.0.0.1";
const socketPort = +parsed["socket-port"] || 65432;

if (!apiKey || !tokenId) {
  logger.error("[WEBHOOK AGENT] Error: --api-key or --token-id not provided");
  process.exit(1);
}

export function sendDataToSocket(host: string, port: number, message: string) {
  const client = new net.Socket();

  client.connect(port, host, () => {
    logger.info(`[WEBHOOK AGENT] Connected to socket at ${host}:${port}`);
    client.write(message);
    client.end(); // cierra la conexión tras enviar
  });

  client.on("error", (err) => {
    logger.error("[WEBHOOK AGENT] Socket error:", err.message);
  });

  client.on("close", () => {
    logger.info("[WEBHOOK AGENT] Connection closed");
  });
}

const headers = apiKey ? { "Api-Key": apiKey } : {};
const echo = new Echo({
  host: process.env.WH_WS_HOST ?? "wss://ws.webhook.site",
  broadcaster: "socket.io",
  client,
  auth: { headers },
});

let channel = echo.private(`token.${tokenId}`);

channel.socket.on("connect", (data: any) => {
  logger.info(
    "[WEBHOOK AGENT] Connected to Websocket. Listening for requests.",
    { data }
  );
  if (!apiKey) {
    logger.info(
      "[WEBHOOK AGENT] Warning: If token is associated with a Webhook.site account, specify an API key.",
      { data }
    );
  }
});

channel.socket.on("error", (err: any) => {
  logger.error("[WEBHOOK AGENT]", err, "WS: Error");
});

channel.error((err: any) => {
  logger.error("[WEBHOOK AGENT]", err, "WS: Error");
});

channel.listen(".request.created", (data: RequestReceived) => {
  logger.info("[WEBHOOK AGENT] Request received => ", data.request.content);
  sendDataToSocket(socketHost, socketPort, data.request.content.toString());
});
