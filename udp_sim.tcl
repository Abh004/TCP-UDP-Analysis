set ns [new Simulator]

set tracefile "udp_output.tr"
set namfile "udp_output.nam"
set tf [open $tracefile w]
set nf [open $namfile w]
$ns trace-all $tf
$ns namtrace-all $nf

set throughput_file [open "udp_throughput.tr" w]

set n0 [$ns node]
set n1 [$ns node]

$ns duplex-link $n0 $n1 2Mb 10ms DropTail
$ns queue-limit $n0 $n1 50

set udp [new Agent/UDP]
$udp set packetSize_ 1000
$ns attach-agent $n0 $udp

set loss_monitor [new Agent/LossMonitor]
$ns attach-agent $n1 $loss_monitor
$ns connect $udp $loss_monitor

set cbr [new Application/Traffic/CBR]
$cbr attach-agent $udp
$cbr set type_ CBR
$cbr set packet_size_ 1000
$cbr set rate_ 1.5Mb  # Send at 1.5Mbps
$cbr set random_ false

set total_bytes 0
set prev_bytes 0

proc record {} {
    global ns loss_monitor throughput_file prev_bytes
    
    # Get current time
    set now [$ns now]
    
    # Get bytes from loss monitor
    set bytes [$loss_monitor set bytes_]
    
    # Calculate throughput in bps (bits per second)
    set time_interval 0.1
    set bytes_interval [expr $bytes - $prev_bytes]
    set throughput [expr $bytes_interval * 8.0 / $time_interval]
    
    # Store current bytes count for next interval
    set prev_bytes $bytes
    
    # Write throughput to file
    puts $throughput_file "$now $throughput"
    
    # Schedule next recording
    $ns at [expr $now + $time_interval] "record"
}

$ns at 0.0 "record"
$ns at 0.5 "$cbr start"
$ns at 9.5 "$cbr stop"
$ns at 10.0 "finish"

proc finish {} {
    global ns tf nf throughput_file loss_monitor
    $ns flush-trace
    close $tf
    close $nf
    close $throughput_file
    
    puts "UDP Simulation completed."
    puts "Total bytes received: [$loss_monitor set bytes_]"
    puts "You can now run: 'nam udp_output.nam' to visualize the simulation"
    puts "Check 'udp_throughput.tr' for throughput data"
    exit 0
}

# Run simulation
$ns run