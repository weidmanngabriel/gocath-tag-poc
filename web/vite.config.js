import {defineConfig} from 'vite';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
export default defineConfig({base:'/gocath-tag-poc/',build:{rollupOptions:{input:{dashboard:resolve(root,'index.html'),rc:resolve(root,'rc/index.html')}}}});
