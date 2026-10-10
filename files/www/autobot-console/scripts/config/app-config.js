(function (global) {
  const baseConfig = {
    api: "http://127.0.0.1:5555/api/",
    action: "action",
    robot: "robot",
    schedule: "schedule",
    config: "config",
  };

  function withTrailingSlash(url) {
    if (!url) return "";
    return url.endsWith("/") ? url : `${url}/`;
  }

  function buildEndpoint(segment = "") {
    const normalizedSegment = segment.replace(/^\/+/, "");
    return `${withTrailingSlash(baseConfig.api)}${normalizedSegment}`;
  }

  global.AutobotAppConfig = Object.freeze({
    ...baseConfig,
    endpoint: (segment) => buildEndpoint(segment ?? ""),
  });
})(window);
