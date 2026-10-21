export function csvCell(value:unknown){
 const text=value==null?'':typeof value==='object'?JSON.stringify(value):String(value);
 return '"'+text.replaceAll('"','""')+'"';
}
export function comparisonCSV(compare:any[]){
 const keys=Object.keys(compare[0].meta.summary);
 return [['session','policy',...keys],...compare.map(c=>[c.meta.id,c.meta.policy,...keys.map(k=>c.meta.summary[k])])].map(row=>row.map(csvCell).join(',')).join('\r\n');
}
