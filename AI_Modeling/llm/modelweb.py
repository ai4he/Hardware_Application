import re
import sys
import json
import time
import openai
# from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, jsonify

# load_dotenv()
sessions = {}
session_var = 'session_id'
context_var = 'context_val'
input_var = 'input_val'
context_state = 'GET_GOALS'
input_state = 'GET_ACTIVITIES'
reflection_state = 'GIVE_REFLECTION'
response_state = 'GIVE_FEEDBACK'
conclusion_state = 'GIVE_CONCLUSION'
stop_tokens = [f'{input_state}:']
finish_tokens = [f'{conclusion_state}:']
track_tokens_arr = stop_tokens + finish_tokens
loop_return = 'STATUS_RETURN'
loop_finish = 'STATUS_FINISH'
loop_states = False

system_msg = f"""I want you to help me to regulate the amount of time I spend in activities that are not contributing to achieving my goals. In specific, I will provide the last activities that I have completed lately. I want you to notify me if you consider that the ratio of leisure time is higher than productive time. You must follow the following structure:

{context_state}: You will get from me a description of my goals. You will align with my goals and become intrinsically motivated to achieve them.
{input_state}: You will get from me a list of activities executed on my computer.
{reflection_state}: You will assess how well I am using my time to achieve the goals while keeping a work-life balance.
{response_state}: You will evaluate if the ratio of leisure and productive time, and provide me brief feedback, no more than 255 characters.
... (this {input_state}/{reflection_state}/{response_state} can repeat N times)
{conclusion_state}: You conclude the session if you consider I am advancing toward my goals.

Begin!
"""

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
  session_id = request.form[session_var]
  context_val = request.form[context_var]
  input_val = request.form[input_var]
  output = endpoint(session_id, context_val, input_val)
  session_id = output[session_var]
  # return jsonify(session_id=session_id, goal=goal, events=events)
  return jsonify(output)

@app.route('/test', methods=['GET', 'POST'])
def test():
  session_id, goal, events = None, None, None
  if request.method == 'POST':
    session_id = request.form[session_var]
    context_val = request.form[context_var]
    input_val = request.form[input_var]
  return render_template('test.html', session_id=session_id, context_val=context_val, input_val=input_val)

def get_session():
  return create_session()

def create_session():
  session_id = str(time.time())
  session = sessions[session_id] = {}
  session['messages'] = []
  session[input_var] = []
  session['initial'] = True
  session['finished'] = False
  return session_id

def finish_process(session_id):
  global sessions
  session = sessions[session_id]
  if session['finished']:
    return True
  if session['initial']:
    return False
  return False

def chat_completion(session_id, query, stop_tokens, track_tokens_arr):
  global sessions
  session = sessions[session_id]
  print('')
  found_token = False
  max_length = 0
  for token in track_tokens_arr:
    if len(token) > max_length:
      max_length = len(token)

  session['messages'].append({"role": "user", "content": query})  
  
  # print(session['messages'])

  response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=session['messages'],
    stream=True
  )

  reply = ''
  for stream_resp in response:
    if 'content' in stream_resp["choices"][0]['delta']:
      token = stream_resp["choices"][0]["delta"]["content"]
      reply += token
      window = reply[-1*(max_length+1):]
      # print(token)
      sys.stdout.write(token)
      for finish_token in finish_tokens:
        if finish_token in window:
          session['finished'] = True
      for stop_token in stop_tokens:
        if stop_token in window:
          found_token = True
          response.close()
          break

  # reply = response["choices"][0]["message"]["content"]
  session['last_reply'] = reply
  return reply

def parse_text(text):
  sections = re.split(r'\n(?=[A-Z_]+:)', text)
  result = {}
  for section in sections:
    if ':' in section:
      title, content = section.split(':', 1)
      result[title.strip()] = content.strip()
    else:
      result['NO_SECTION'] = section.strip()
  return result

def enforce_next(session_id, next_step):
  global sessions
  session = sessions[session_id]
  next_action = f"\n{next_step} "
  query = next_action
  session['messages'].append({"role": "user", "content": query})
  reply = chat_completion(session_id, query, stop_tokens, track_tokens_arr)
  session['messages'].append({"role": "assistant", "content": reply})
  reply = next_action + reply
  sections = parse_text(reply)
  return sections

def process_next(session_id, query, next_step, enforce=False):
  global sessions
  session = sessions[session_id]
  print(next_step)
  reply = chat_completion(session_id, query, stop_tokens, track_tokens_arr)
  session['messages'].append({"role": "assistant", "content": reply})
  reply = next_action + reply
  sections = parse_text(reply)
  if enforce and next_step not in reply:
    sections_enf = enfonce_next(session_id, next_step)
    for section in sections_enf:
      sections[section] = sections_enf[section]
  return sections

def process(session_id):
  global sessions
  session = sessions[session_id]
  result = {}
  if session['initial']:
    session['initial'] = False
    sections = process_input(session_id, {f'{context_state}:': session[context_var], f'{input_state}:': session[input_var][-1]}, {f'{reflection_state}:':''}, enforce=f'{response_state}:')
    for section in sections:
      result[section] = sections[section]
  else:
    sections = process_input(session_id, {f'{input_state}:': session[input_var][-1]}, {f'{reflection_state}:':''})
    for section in sections:
      result[section] = sections[section]
    if loop_states:
      sections = loop_or_finish(session_id, f'{response_state}:', f'{conclusion_state}:', loop_return, loop_finish)
      for section in sections:
        result[section] = sections[section]
  return result

def process_input(session_id, input_dict, output_dict, enforce=False):
  global sessions
  session = sessions[session_id]
  query = ''
  for key in input_dict:
    query += f'\n{key} {input_dict[key]}'
  output_state = ''
  for key in output_dict:
    output_state = key
    query += f'\n{key} {output_dict[key]}'
  session['messages'].append({"role": "user", "content": query})
  print(output_state)
  reply = chat_completion(session_id, query, stop_tokens, track_tokens_arr)
  session['messages'].append({"role": "assistant", "content": reply})
  reply = f'{output_state} ' + reply
  sections = parse_text(reply)
  if enforce and enforce not in reply:
    sections_enf = enforce_next(session_id, enforce)
    for section in sections_enf:
      sections[section] = sections_enf[section]
  return sections

def loop_or_finish(session_id, loop_state, finish_state, loop_token, finish_token):
  global sessions
  session = sessions[session_id]
  sections = {}
  if loop_token in session['last_reply'] and loop_state not in session['last_reply']:
    print(loop_state)
    sections = enforce_next(session_id, loop_state)
  elif finish_token in session['last_reply'] and finish_state not in session['last_reply']:
    print(finish_state)
    sections = enforce_next(session_id, finish_state)
  return sections

def run(session_id, input_val):
  global sessions
  session = sessions[session_id]
  if not finish_process(session_id):
    session[input_var].append(input_val)
    output = process(session_id)
    output[session_var] = session_id
    output['status'] = 'ACTIVE'
    return output
  else:
    output = {}
    output[session_var] = session_id
    output['status'] = 'FINISHED'
    return output

def init(context_val):
  global sessions
  session_id = get_session()
  session = sessions[session_id]
  session['messages'].append({"role": "system", "content": system_msg})

  # goal = "I want to learn how to create a date picker on HTML and javascript that helps me to filter an HTML table."
  session[context_var] = context_val
  return session_id

def endpoint(session_id, context_val, input_val):
  if session_id:
    return run(session_id, input_val)
  else:
    session_id = init(context_val)
    return run(session_id, input_val)

# if __name__ == '__main__':
#     app.run(debug=True)