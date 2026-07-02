import { execFileSync, spawn } from 'node:child_process'
import { mkdirSync, rmSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const e2eDir = resolve(scriptDir, '..')
const rootDir = resolve(e2eDir, '..')
const backendDir = resolve(rootDir, 'backend')
const runtimeDir = resolve(e2eDir, '.runtime')
const databasePath = resolve(runtimeDir, 'homevault-e2e.db')
const uploadDir = resolve(runtimeDir, 'uploads')
const sqlitePath = databasePath.replace(/\\/g, '/')

const env = {
  ...process.env,
  HOMEVAULT_DATABASE_URL: `sqlite:///${sqlitePath}`,
  HOMEVAULT_SECRET_KEY: 'homevault-e2e-secret-key-at-least-32-bytes',
  HOMEVAULT_ADMIN_USERNAME: 'admin',
  HOMEVAULT_ADMIN_PASSWORD: 'ChangeMe123!',
  HOMEVAULT_UPLOAD_DIR: uploadDir
}

function runPython(args) {
  execFileSync('python', args, {
    cwd: backendDir,
    env,
    stdio: 'inherit'
  })
}

rmSync(databasePath, { force: true })
rmSync(uploadDir, { force: true, recursive: true })
mkdirSync(uploadDir, { recursive: true })

runPython(['-m', 'alembic', 'upgrade', 'head'])
runPython(['-m', 'app.cli'])
runPython([resolve(scriptDir, 'seed-e2e-data.py')])

const server = spawn(
  'python',
  ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
  {
    cwd: backendDir,
    env,
    stdio: 'inherit'
  }
)

function stopServer() {
  if (!server.killed) server.kill()
}

process.on('SIGINT', stopServer)
process.on('SIGTERM', stopServer)

server.on('exit', (code, signal) => {
  if (signal) process.exit(0)
  process.exit(code ?? 0)
})
