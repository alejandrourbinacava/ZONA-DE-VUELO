import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// Concurrencia automatica (segun nucleos de la maquina); en local se puede forzar con RENDER_CONCURRENCY.
// HD 720p (composicion 1920x1080 x 2/3 = 1280x720). Aligera el render.
Config.setScale(2 / 3);
