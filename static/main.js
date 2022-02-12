var socket = io({ forceNew:true })
var playerNum

window.onload = ()=>{
    socket.emit('join')
}

function sendUpdate(){
    socket.emit('do_turn', Math.max(Number(document.getElementById("RaiseAmount").value), 0))
}
function fold(){
    socket.emit('do_turn', 'fold')
}
function call(){
    socket.emit('do_turn', 0)
}

socket.on('set_data', (data)=>{
    playerNum = data[1]
    document.getElementById('hand').innerHTML = data[0]
    document.getElementById('number').innerHTML = playerNum
    document.getElementById('pot').innerHTML = data[2]
    document.getElementById('bet').innerHTML = data[3]
})
socket.on('set_turn', (num)=>{
    document.getElementById('current').innerHTML = num
})

socket.on('update_pot', (value)=>{
    document.getElementById('pot').innerHTML = value
})

socket.on('update_bet', (value)=>{
    document.getElementById('bet').innerHTML = value
})

socket.on('set_deal', (deal)=>{
    document.getElementById('board').innerHTML = deal
})

socket.on('declare_winner', (win_data)=>{
    let newstr = ''
    for(let i of win_data[0]){
        newstr += i[0]+':'+i[1]+';'
    }
    document.getElementById('winners').innerHTML = newstr + '(' + win_data[1] + ')'

})

socket.on('show_hands', (hands)=>{
    document.getElementById('results').style.display = "block"
    document.getElementById('hands').innerHTML = hands
})

socket.on('declare_scores', (scores)=>{
    console.log(scores)
})