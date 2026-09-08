from factlayer.normalization import normalize_value,normalize_entity

def test_currency_scale():
 v=normalize_value('₹12 crore',None); assert v.normalized_value==120000000 and v.normalized_unit=='INR'
def test_entity(): assert normalize_entity('Delhivery Limited')=='delhivery'
