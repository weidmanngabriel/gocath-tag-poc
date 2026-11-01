import unittest
from src.rc_tags import tag_sync
from src.rc_catalog import publish_questions,sync,public_feed

class TagTests(unittest.TestCase):
    def test_independent_tag_version(self):
        cfg={'criteria':[{'id':'prayer','weight':1}],'tag_prompt':'Keywords','tag_model':'gpt-4.1-mini','tag_limit':8}
        event={'url':'https://www.regnumchristi.eu/demnaechst/?vid=21','title':'Gebet','description':'Jugendgebet'}
        state={'schema_version':1,'events':{}}
        publish_questions(state,cfg)
        sync(state,[event],lambda *a:{'criteria_scores':[{'id':'prayer','score':0.8}]})
        before=state['events']['rc-21']['classification'].copy()
        generator=lambda e,c,u,s:['Jugendgebet']
        self.assertEqual(tag_sync(state,[event],cfg,generator)['tagged'],1)
        self.assertEqual(tag_sync(state,[event],cfg,generator)['tagged'],0)
        cfg['tag_prompt']='New keywords'
        self.assertEqual(tag_sync(state,[event],cfg,generator)['tagged'],0)
        self.assertEqual(tag_sync(state,[event],cfg,generator,mode='retag')['tagged'],1)
        self.assertEqual(state['events']['rc-21']['classification'],before)
        self.assertEqual(public_feed(state)['events'][0]['tagging']['tags'],['Jugendgebet'])

    def test_unclassified_event_is_not_tagged(self):
        cfg={'tag_prompt':'keywords','tag_model':'gpt-4.1-mini','tag_limit':8}
        event={'url':'https://www.regnumchristi.eu/demnaechst/?vid=22','title':'Gebet','description':'Gebet'}
        state={'events':{'rc-22':{'event':event}}}
        self.assertEqual(tag_sync(state,[event],cfg,lambda *args: self.fail('must not tag'))['tagged'],0)

    def test_prompt_cannot_change_technical_output_format(self):
        from unittest.mock import Mock,patch
        from src.rc_tags import generate
        cfg={'tag_prompt':'Bitte gib standard_tags und reason zurück','tag_model':'gpt-4.1-mini','tag_limit':3}
        fake=Mock(ok=True)
        fake.json.return_value={'status':'completed','output':[{'content':[{'type':'output_text','text':'{"tags":["Eheseminar"]}'}]}]}
        with patch('src.rc_tags.requests.post',return_value=fake) as api:
            result=generate({'title':'Eheseminar'},'test-key',cfg,{},[{'id':'ehe','label':'Ehe','matched':True}])
        self.assertEqual(result,['Eheseminar'])
        payload=api.call_args.kwargs['json']
        self.assertEqual(payload['text']['format']['schema']['required'],['tags'])
        supplied=__import__('json').loads(payload['input'])
        self.assertEqual(supplied['klassifizierung'][0]['id'],'ehe')
        self.assertIn('Bitte gib standard_tags und reason zurück',payload['instructions'])
        self.assertIn('Maximal 3 Tags',payload['instructions'])
        self.assertNotIn('standard_tags',payload['text']['format']['schema']['properties'])
