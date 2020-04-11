let chatInput = $('#chat-input');
let chatButton = $('#btn-send');
let userList = $('#user-list');
let messageList = $('#messages');
let scoreboard = $('#scoreboard');

function getRoomName() {
  return new URL(window.location.href).pathname.split('/').pop();
}

function getGameUsers(room) {
  //$.getJSON(`/api/v1/user/?room=${room}`, function(data) {
  console.log(`/game_users/${room}`)
  $.getJSON(`/game_users/${room}`, function(data) {
    console.log(data)
    userList.children('.user').remove();
    drawUsers(data.red_team, 'redteam')
    drawUsers(data.blue_team, 'blueteam')
    // $('.user').click(function() {
    //   userList.children('.active').removeClass('active');
    //   let selected = event.target;
    //   $(selected).addClass('active');
    // });
  });
}
function drawUsers(teamList, teamClass) {
  for (let i = 0; i < teamList.length; i++) {
    let [name, count] = teamList[i];
    const userItem = `<li class="list-group-item user ${teamClass}">
      ${name} (${count} words)
    </li>`;
    $(userItem).appendTo('#user-list');
  }
}
function getGameScore(room) {
  console.log(`/api/v1/game/?room=${room}`);
  $.getJSON(`/api/v1/game/?room=${room}`, function(data) {
    console.log(data.results)
    drawGameState(data.results[0]);
  });
}

function drawGameState(data) {
  console.log('drawGameState')
  console.log(data)
  // userList.children('.score').remove();
  $('#redscore').text('Red score: ' + data.red_points)
  $('#bluescore').text('Blue score: ' + data.blue_points)
  $('#round').text('Round: ' + data.current_round)
  $('#guessingTeam').text('Guessing Team: ' + data.current_guessing_team)
  $('#numRemainingWords').text('Remaining words: ' + data.num_words_remaining)
  let timeLeftStr =
      (data.time_left === undefined) ? data.remaining_seconds : data.time_left
  $('#timer').text('Timer: ' + timeLeftStr)
  $('#clueGiver').text('Giver: ' + data.clue_giver)
  let $curWord = $('#currentWord')
  if (data.clue_giver === currentUser && data.time_left > 0) {
    console.log('clue giver!:')
    $curWord.text('Current word: ' + data.current_word)
    $curWord.css('background-color', '#b8edb5')
  }
  else {
    $curWord.text('Current word: ')
    $curWord.css('background-color', '#fff')
  }
}


function drawMessage(message, private = false, admin = false) {
  let position = 'left';
  // currentUser defined in core/chat.html: request.user.username
  if (message.user === currentUser) position = 'right';

  let privateSpan =
      private ? ' <span class="small">Visible only to you</span>' : '';
  let adminStr = admin ? 'admin' : '';
  const date = new Date(message.timestamp);
  const messageItem = `
            <li class="message ${position} ${adminStr}">
                <div class="avatar">${message.user}</div>
                    <div class="text_wrapper">
                        ${privateSpan}
                        <div class="text">${message.body}<br>
                            <span class="small">${date}</span>
                    </div>
                </div>
            </li>`;
  $(messageItem).appendTo('#messages');
}

function getConversation(room) {
  $.getJSON(`/api/v1/message/?room=${room}`, function(data) {
    messageList.children('.message').remove();
    for (let i = data['results'].length - 1; i >= 0; i--) {
      drawMessage(data['results'][i]);
    }
    messageList.animate({scrollTop: messageList.prop('scrollHeight')});
  });
}

function getMessageById(message_id) {
  $.getJSON(`/api/v1/message/${message_id}/`, function(data) {
    // if (data.user === currentRecipient ||
    //     (data.recipient === currentRecipient && data.user == currentUser)) {
    drawMessage(data);
    // }
    messageList.animate({scrollTop: messageList.prop('scrollHeight')});
  });
}

function sendMessage(room, body) {
  $.post('/api/v1/message/', {room: room, body: body})
      .fail(function(jqXHR, textStatus, error) {
        console.log('Post error: ' + error);
      });
}

function sendCommand(room, body) {
  $.post(
       '/command/', {
         csrfmiddlewaretoken: window.CSRF_TOKEN,
         room: room,
         body: body,
       },
       function(data) {
         console.log(data)
       })
      .fail(function(jqXHR, textStatus, error) {
        console.log('Post error: ' + error);
      });
}

function setCurrentRoom(roomname) {}


function enableInput() {
  chatInput.prop('disabled', false);
  chatButton.prop('disabled', false);
  chatInput.focus();
}

function disableInput() {
  chatInput.prop('disabled', true);
  chatButton.prop('disabled', true);
}

$(document).ready(function() {
  let currentRoom = getRoomName();
  getGameUsers(currentRoom);
  disableInput();

  //    let socket = new
  //    WebSocket(`ws://127.0.0.1:8000/?session_key=${sessionKey}`);
  // window.location.host   ->  "localhost:8000"
  // window.location.pathname -> "/room/general"
  // var socket = new WebSocket(
  //     'ws://' + window.location.host + '/ws' + window.location.pathname +
  //     '/?session_key=${sessionKey}')
  var ws_scheme = window.location.protocol == 'https:' ? 'wss' : 'ws';
  var ws_path = ws_scheme + '://' + window.location.host + '/ws' +
      window.location.pathname + '/?session_key=${sessionKey}';
  console.log('Connecting to ' + ws_path);
  var socket = new ReconnectingWebSocket(ws_path);

  chatInput.keypress(function(e) {
    if (e.keyCode == 13) chatButton.click();
  });

  chatButton.click(function() {
    let msg = chatInput.val()
    if (msg.length < 1) {
      return
    }
    if (msg.startsWith('/')) {
      sendCommand(getRoomName(), msg);
    } else {
      sendMessage(getRoomName(), msg);
    }
    chatInput.val('');
  });

  getConversation(currentRoom);
  getGameScore(currentRoom);
  enableInput();

  socket.onmessage = function(message) {
    let msg_data = JSON.parse(message.data)
    console.log(msg_data)
    if (msg_data.message_id) {
      getMessageById(msg_data.message_id);
    }
    else if (msg_data.message && msg_data.message.body) {
      if (msg_data.private) {
        if (msg_data.submitter === currentUser) {
          drawMessage(msg_data.message, msg_data.private, msg_data.admin);
          messageList.animate({scrollTop: messageList.prop('scrollHeight')});
        }
      } else {
        drawMessage(msg_data.message, msg_data.private, msg_data.admin);
        messageList.animate({scrollTop: messageList.prop('scrollHeight')});
      }
    }
    if (msg_data.game_update) {
      console.log('received game update')
      updateGame(currentRoom, msg_data.game_state);
    }
  };
});

function updateGame(currentRoom, gameState) {
  console.log('updateGame')
  drawGameState(gameState);
  getGameUsers(currentRoom);
}