set ns [new Simulator]

set tracefile "tcp_output.tr"
set namfile "tcp_output.nam"
set tf [open $tracefile w]
set nf [open $namfile w]
$ns trace-all $tf
$ns namtrace-all $nf

set throughput_file [open "tcp_throughput.tr" w]

set n0 [$ns node]
set n1 [$ns node]

$ns duplex-link $n0 $n1 2Mb 10ms DropTail
$ns queue-limit $n0 $n1 50

set tcp [new Agent/TCP]
$tcp set window_ 20
$tcp set packetSize_ 1000
$ns attach-agent $n0 $tcp

set sink [new Agent/TCPSink]
$ns attach-agent $n1 $sink
$ns connect $tcp $sink

set ftp [new Application/FTP]
$ftp attach-agent $tcp
$ftp set type_ FTP

proc record {} {
    global sink throughput_file ns
    
    # Get current time
    set now [$ns now]
    
    # Get bytes received by sink
    set bytes_received [$sink set bytes_]
    
    # Calculate throughput (bps)
    set time_interval 0.1
    set throughput [expr $bytes_received * 8.0 / $time_interval]
    
    # Reset bytes counter
    $sink set bytes_ 0
    
    # Write throughput to file
    puts $throughput_file "$now $throughput"
    
    # Schedule next recording
    $ns at [expr $now + $time_interval] "record"
}

$ns at 0.0 "record"
$ns at 0.5 "$ftp start"
$ns at 9.5 "$ftp stop"
$ns at 10.0 "finish"

proc finish {} {
    global ns tf nf throughput_file
    $ns flush-trace
    close $tf
    close $nf
    close $throughput_file
    puts "Simulation completed."
    puts "You can now run: 'nam tcp_output.nam' to visualize the simulation"
    puts "Check 'throughput.tr' for throughput data"
    exit 0
}

# Run simulation
$ns run