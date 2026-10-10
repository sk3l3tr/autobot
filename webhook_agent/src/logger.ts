import path from "path";
import { existsSync, mkdirSync } from "fs";
import { createLogger, format, transports } from "winston";

//Ruta del ejecutable y carpeta de logs
const exeDir = path.dirname(process.execPath);
const logsDir = path.resolve(exeDir, "..", "logs");
if (!existsSync(logsDir)) mkdirSync(logsDir, { recursive: true });

// Creamos el logger.
export const logger = createLogger({
  level: "info", // nivel mínimo. 'info' recoge info, warn, error, etc.
  format: format.combine(
    format.timestamp(),
    format.printf(
      ({ timestamp, level, message }) =>
        `${timestamp} [${level.toUpperCase()}] ${message}`
    )
  ),
  transports: [
    new transports.Console(),
    new transports.File({
      filename: path.join(logsDir, "w3bh00k_4g3nt.log"),
    }),
  ],
});
