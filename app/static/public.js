import {$,values,options,message} from './core.js';
import {api} from './api.js';
import {render} from './render.js';
async function load(){const state=await api('public?'+new URLSearchParams(values($('#filters'))));options($('#filter-category'),state.categories,'Semua kategori');render(state,false,false);}
$('#filters').addEventListener('submit',e=>{e.preventDefault();load().catch(e=>message(e.message));});load().catch(e=>message(e.message));
