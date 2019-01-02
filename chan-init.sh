#!/bin/bash
read -d '' query<<HERE
initiator_id=ak_2VsncWAk9qkA8SAY8zpcympSaCN313TV9GjAPZ9XQUFMSz4vTf\
&responder_id=ak_25UPgAhVxTrq6CCyjDYhMpPadW6QLHNxtV5a2je12RGk1Rfmjt\
&lock_period=10\
&push_amount=2\
&initiator_amount=10\
&responder_amount=10\
&channel_reserve=2\
&ttl=0\
&timeout_accept=3600000\
&timeout_funding_create=3600000\
&timeout_funding_sign=3600000\
&timeout_funding_lock=3600000\
&timeout_idle=3600000\
&timeout_open=3600000\
&timeout_sign=3600000\
&role=initiator\
&host=localhost\
&port=1234
HERE
#refer to https//github.com/aeternity/protocol/blob/master/epoch/api/channels_api_usage.md, section Channel Parameters, for parameter documentation

#initiator connects to node
echo -e "Connecting to localhost:3014/channel?$query"

wscat $@ --connect "localhost:3014/channel?$query"
