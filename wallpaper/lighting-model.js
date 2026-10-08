export function lightingAt(date,settings,override='auto'){
 if(!settings)return {a:'day',b:null,mix:0};
 if(override!=='auto'&&override in settings.phases)return {a:override,b:null,mix:0};
 const schedule=settings.schedule,seconds=date.getHours()*3600+date.getMinutes()*60+date.getSeconds()+date.getMilliseconds()/1000;
 let index=schedule.length-1;
 for(let i=0;i<schedule.length;i++)if(seconds>=schedule[i].minute*60)index=i;
 const current=schedule[index],elapsed=(seconds-current.minute*60+86400)%86400;
 if(elapsed>=settings.fadeSeconds)return {a:current.phase,b:null,mix:0};
 const t=elapsed/settings.fadeSeconds;
 return {a:schedule[(index+schedule.length-1)%schedule.length].phase,b:current.phase,mix:t*t*(3-2*t)};
}
