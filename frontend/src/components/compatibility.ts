export function compatibleSessions(compare:any[]):boolean{
 if(!compare.length)return true;
 const keys=['profile','seed','scale','asset_id','asset_fingerprint','source_identity','controller_version','common_settings_identity','model_checksum','model_file_sha256','duration_limit_s','benchmark'];
 return compare.every(x=>x.meta.status==='finished'&&!x.meta.summary?.interacted&&x.meta.asset_fingerprint&&x.meta.source_identity&&x.meta.common_settings_identity&&Math.abs(x.meta.summary?.observed_s-compare[0].meta.summary?.observed_s)<2&&keys.every(k=>x.meta[k]===compare[0].meta[k])&&(x.meta.policy!=='ml'||x.meta.summary?.forest_prediction_count>0));
}
