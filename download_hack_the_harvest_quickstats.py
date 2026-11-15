#!/usr/bin/env python3
"""Download USDA NASS Quick Stats data relevant to grain/silage classification
into the 'Quickstats Data' folder next to this script (override with --output).
Requires: NASS_API_KEY environment variable (free from https://quickstats.nass.usda.gov/api).
Usage: python download_hack_the_harvest_quickstats.py --start 2015 --end 2025
Only published aggregates are retrieved; this is not field-level ground truth.
"""
import argparse, csv, json, os, pathlib, time, urllib.parse, urllib.request, urllib.error

API='https://quickstats.nass.usda.gov/api/api_GET/'
HERE=pathlib.Path(__file__).resolve().parent
DEFAULT_OUT=HERE/'Quickstats Data'
# name -> (query filters, geographic levels). Filters are exact Quick Stats parameters.
DATASETS={
 'corn_silage_harvested_acres': ({'commodity_desc':'CORN','util_practice_desc':'SILAGE','statisticcat_desc':'AREA HARVESTED','unit_desc':'ACRES'},('COUNTY','STATE')),
 'corn_grain_harvested_acres': ({'commodity_desc':'CORN','util_practice_desc':'GRAIN','statisticcat_desc':'AREA HARVESTED','unit_desc':'ACRES'},('COUNTY','STATE')),
 'corn_planted_acres': ({'commodity_desc':'CORN','statisticcat_desc':'AREA PLANTED','unit_desc':'ACRES'},('COUNTY','STATE')),
 'corn_grain_yield_bu_acre': ({'commodity_desc':'CORN','util_practice_desc':'GRAIN','statisticcat_desc':'YIELD','unit_desc':'BU / ACRE'},('COUNTY','STATE')),
 'corn_silage_yield_tons_acre': ({'commodity_desc':'CORN','util_practice_desc':'SILAGE','statisticcat_desc':'YIELD','unit_desc':'TONS / ACRE'},('COUNTY','STATE')),
 'milk_cow_inventory': ({'commodity_desc':'CATTLE','class_desc':'COWS, MILK','statisticcat_desc':'INVENTORY'},('COUNTY','STATE')),
 'cattle_calves_inventory': ({'short_desc':'CATTLE, INCL CALVES - INVENTORY'},('COUNTY','STATE')),
 'corn_irrigated_acres': ({'commodity_desc':'CORN','prodn_practice_desc':'IRRIGATED','statisticcat_desc':'AREA HARVESTED'},('COUNTY','STATE')),
 'corn_production': ({'commodity_desc':'CORN','statisticcat_desc':'PRODUCTION'},('COUNTY','STATE')),
 'corn_prices_received': ({'commodity_desc':'CORN','statisticcat_desc':'PRICE RECEIVED'},('STATE','NATIONAL')),
}
FIELDS=['source_desc','sector_desc','group_desc','commodity_desc','class_desc','prodn_practice_desc','util_practice_desc','statisticcat_desc','unit_desc','short_desc','domain_desc','domaincat_desc','agg_level_desc','state_alpha','state_name','state_fips_code','county_name','county_code','asd_desc','year','freq_desc','reference_period_desc','Value','CV (%)','load_time']

def fetch(params,key):
    q=urllib.parse.urlencode(dict(params,key=key,format='JSON'))
    req=urllib.request.Request(API+'?'+q,headers={'User-Agent':'HackTheHarvestResearch/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=90) as response:
            return json.load(response)['data']
    except urllib.error.HTTPError as exc:
        detail=exc.read(500).decode('utf-8','replace')
        raise RuntimeError(f'HTTP {exc.code}: {detail}') from exc

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--start',type=int,default=2015)
    p.add_argument('--end',type=int,default=2025)
    p.add_argument('--output',default=str(DEFAULT_OUT))
    p.add_argument('--skip-existing',action='store_true',help='resume: skip datasets whose CSV already exists')
    args=p.parse_args()
    key=os.environ.get('NASS_API_KEY')
    if not key: p.error('Set NASS_API_KEY to your free USDA Quick Stats API key first.')
    dest=pathlib.Path(args.output);dest.mkdir(parents=True,exist_ok=True)
    report=[]
    for category,(filters,levels) in DATASETS.items():
        for level in levels:
            path=dest/f'{category.lower()}_{level.lower()}_{args.start}_{args.end}.csv'
            if args.skip_existing and path.exists():
                print('Skipping existing',path);continue
            count=0
            tmp=path.with_suffix('.csv.part')
            with tmp.open('w',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader()
                for year in range(args.start,args.end+1):
                    try:
                        records=fetch(dict(filters,agg_level_desc=level,year=year),key)
                        if len(records)>=50000:
                            print('WARNING: request may be truncated at 50,000 records:',category,level,year)
                        writer.writerows(records);count+=len(records)
                        print(category,level,year,len(records))
                    except Exception as exc:
                        print('FAILED',category,level,year,exc)
                        report.append({'category':category,'level':level,'year':year,'error':str(exc)})
                    time.sleep(.25)
            tmp.replace(path)
            print('Saved',path,'rows',count)
    (dest/'download_errors.json').write_text(json.dumps(report,indent=2))
    print('Done. Filter short_desc, statisticcat_desc, util_practice_desc, domain_desc, and unit_desc for analysis.')

if __name__=='__main__': main()
