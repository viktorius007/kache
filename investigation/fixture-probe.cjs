const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const root = __dirname;
const mode = process.argv[2] || 'restore-only';
const dir = fs.mkdtempSync(path.join(root, 'fixtures/job-'));
const tool = path.join(dir, 'tools/kache/0.15.1', os.arch());
fs.mkdirSync(tool, {recursive:true});
fs.writeFileSync(tool + '.complete', '');
fs.writeFileSync(path.join(tool, 'kache'), '#!/bin/sh\necho "$*" >> "$PROBE_COMMANDS"\ncase "$1" in\n stats) echo "Remote:     s3://fixture-bucket/artifacts";;\n daemon) echo "offline";;\n esac\n');
fs.chmodSync(path.join(tool,'kache'), 0o755);
fs.mkdirSync(path.join(dir,'workspace'));
fs.mkdirSync(path.join(dir,'runtime'));
fs.writeFileSync(path.join(dir,'workspace/Cargo.lock'),'version = 4\n');
const requests = [];
const server = http.createServer((req,res)=>{
  let data=''; req.on('data', chunk=>data+=chunk); req.on('end',()=>{
    requests.push({url:req.url,body:data});
    res.setHeader('content-type','application/json'); res.end('{"ok":false}');
  });
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const env = {
    PATH:process.env.PATH, HOME:path.join(dir,'home'), RUNNER_TOOL_CACHE:path.join(dir,'tools'),
    RUNNER_TEMP:dir, GITHUB_WORKSPACE:path.join(dir,'workspace'), GITHUB_ACTIONS:'true',
    GITHUB_EVENT_NAME:'release', GITHUB_REF:'refs/tags/v1.0', GITHUB_REF_TYPE:'tag',
    GITHUB_REPOSITORY:'fixture/repo', GITHUB_RUN_ID:'1', GITHUB_RUN_ATTEMPT:'1',
    ACTIONS_CACHE_SERVICE_V2:'true', ACTIONS_RUNTIME_TOKEN:'fixture-token',
    ACTIONS_RESULTS_URL:`http://127.0.0.1:${server.address().port}/`,
    INPUT_VERSION:'0.15.1', 'INPUT_GITHUB-CACHE':mode==='disabled'?'false':'true',
    'INPUT_SAVE-CACHE':'false', 'INPUT_CACHE-C-CPP':'false', 'INPUT_NODE-CACHE':'false',
    'INPUT_CACHE-DIR':path.join(dir,'store'), 'INPUT_RUNTIME-DIR':path.join(dir,'runtime'),
    'INPUT_CACHE-KEY-PREFIX':'fixture', 'INPUT_STRICT':'false',
    PROBE_COMMANDS:path.join(dir,'kache-commands.txt'),
  };
  if(mode==='s3'){ Object.assign(env, {'INPUT_S3-BUCKET':'fixture-bucket','INPUT_S3-REGION':'us-east-1','INPUT_S3-PREFIX':'artifacts',INPUT_SYNC:'true'}); }
  const child = spawn(process.execPath,[path.join(root,'upstream/kache-action/dist/setup/index.js')],{cwd:path.join(dir,'workspace'),env});
  let stdout='',stderr=''; child.stdout.on('data',x=>stdout+=x); child.stderr.on('data',x=>stderr+=x);
  const exit = await new Promise(resolve=>child.on('exit',resolve)); server.close();
  const commands=fs.existsSync(env.PROBE_COMMANDS)?fs.readFileSync(env.PROBE_COMMANDS,'utf8'):'';
  const configPath=path.join(dir,'store/kache-action.toml');
  const config=fs.existsSync(configPath)?fs.readFileSync(configPath,'utf8'):'';
  const result={mode,exit,requests,commands,config,stdout,stderr,dir};
  fs.writeFileSync(path.join(root,`evidence/setup-${mode}.json`),JSON.stringify(result,null,2));
  assert.equal(exit,0,stdout+stderr);
  const read = requests.some(r=>r.url.includes('GetCacheEntryDownloadURL')) || commands.includes('sync --pull');
  console.log(JSON.stringify({mode,read,requests:requests.length,commands,config,exit},null,2));
  if(process.argv.includes('--expect-no-read')) assert.equal(read,false,'restore-only publishing still reads cache');
  else assert.equal(read,mode!=='disabled');
  if(mode==='s3') assert.match(config,/remote_readonly = true/);
})().catch(e=>{server.close();console.error(e);process.exitCode=1;});
