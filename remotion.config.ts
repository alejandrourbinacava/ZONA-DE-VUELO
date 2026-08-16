import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
// HD 720p (composicion 1920x1080 x 2/3 = 1280x720). Aligera el render.
Config.setScale(2 / 3);
