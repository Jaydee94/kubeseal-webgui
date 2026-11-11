// Minimal levelled console logger for the UI.
//
// Default level is "debug" on the dev server and "info" in production builds.
// To change it in a running browser (e.g. while debugging a deployment) run
//   localStorage.setItem("kubeseal-webgui:loglevel", "debug")
// and reload. Valid levels: debug, info, warn, error, silent.
//
// IMPORTANT: never pass secret values, file contents or request bodies to the
// logger. Browser consoles get screenshotted, exported and shared.

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40, silent: 100 }
const STORAGE_KEY = 'kubeseal-webgui:loglevel'
const PREFIX = '[kubeseal-webgui]'

function defaultLevel() {
  return import.meta.env.DEV ? 'debug' : 'info'
}

function resolveLevel() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && stored.toLowerCase() in LEVELS) {
      return stored.toLowerCase()
    }
  } catch {
    // localStorage can be unavailable (privacy mode, blocked site data).
  }
  return defaultLevel()
}

let currentLevel = resolveLevel()

export function getLogLevel() {
  return currentLevel
}

export function setLogLevel(level) {
  if (!(level in LEVELS)) {
    throw new Error(`Unknown log level: ${level}`)
  }
  currentLevel = level
}

function emit(level, scope, args) {
  if (LEVELS[level] < LEVELS[currentLevel]) {
    return
  }
  console[level](`${PREFIX} ${new Date().toISOString()} ${level.toUpperCase()} [${scope}]`, ...args)
}

export function createLogger(scope) {
  return {
    debug: (...args) => emit('debug', scope, args),
    info: (...args) => emit('info', scope, args),
    warn: (...args) => emit('warn', scope, args),
    error: (...args) => emit('error', scope, args)
  }
}
