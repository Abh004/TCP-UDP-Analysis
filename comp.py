import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import sys

def parse_trace_file(filename, protocol_tag):
    rtt_values = []
    delays = []
    sent_times = {}        
    jitter_values = []
    total_data_sent = 0
    start_time = None
    end_time = None
    received_packets = 0   
    sent_packets = 0       
    packet_size = 0
        
    try:
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split()
                
                if len(parts) < 12:
                    continue
                    
                event = parts[0]      
                time = float(parts[1]) 
                src = parts[2]        
                dst = parts[3]        
                pkt_type = parts[4]   
                flow_id = parts[7]    
                seq_no = parts[10]    
                
                if start_time is None or time < start_time:
                    start_time = time
                if end_time is None or time > end_time:
                    end_time = time
                
                # Try to get packet size
                try:
                    size = int(float(parts[8])) 
                except ValueError:
                    size = 0
                    
                if pkt_type != protocol_tag:
                    continue
                
                # Sent packets
                if event == '+' and src == '0':  # Packet sent from source node
                    sent_times[seq_no] = time
                    sent_packets += 1
                    total_data_sent += size
                    packet_size = size
                
                # Received packets and RTT 
                elif event == 'r' and dst == '0':  
                    if seq_no in sent_times:
                        rtt = time - sent_times[seq_no]
                        rtt_values.append((time, rtt))
                        received_packets += 1
                
                # Delay
                elif event == 'r' and dst == '1':  
                    if seq_no in sent_times:
                        delay = time - sent_times[seq_no]
                        delays.append((time, delay))
                        
                        if len(delays) > 1:
                            jitter = abs(delays[-1][1] - delays[-2][1])
                            jitter_values.append((time, jitter))
        
        total_time = end_time - start_time if end_time and start_time else 0
        throughput = total_data_sent / total_time if total_time > 0 else 0
        
        rtt_df = pd.DataFrame(rtt_values, columns=['time', 'value']) if rtt_values else pd.DataFrame()
        delay_df = pd.DataFrame(delays, columns=['time', 'value']) if delays else pd.DataFrame()
        jitter_df = pd.DataFrame(jitter_values, columns=['time', 'value']) if jitter_values else pd.DataFrame()
        
        return {
            'rtt': rtt_df,
            'delay': delay_df,
            'jitter': jitter_df,
            'throughput': throughput,
            'sent_packets': sent_packets,
            'received_packets': received_packets,
            'packet_size': packet_size,
            'total_time': total_time,
            'packet_loss': ((sent_packets - received_packets) / sent_packets * 100) if sent_packets > 0 else 0
        }
        
    except FileNotFoundError:
        print(f"Error: File {filename} not found.")
        return {
            'rtt': pd.DataFrame(),
            'delay': pd.DataFrame(),
            'jitter': pd.DataFrame(),
            'throughput': 0,
            'sent_packets': 0,
            'received_packets': 0,
            'packet_size': 0,
            'total_time': 0,
            'packet_loss': 0
        }

def parse_throughput_file(filename):
    times = []
    throughputs = []
    
    try:
        with open(filename, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        time = float(parts[0])
                        throughput = float(parts[1])
                        times.append(time)
                        throughputs.append(throughput)
                    except ValueError:
                        continue
        
        return pd.DataFrame({'time': times, 'value': throughputs})
    
    except FileNotFoundError:
        print(f"Warning: Throughput file {filename} not found.")
        return pd.DataFrame()

def calculate_average(df):
    return df['value'].mean() if not df.empty else 0

def analyze_trace_files(tcp_trace, udp_trace, tcp_throughput_file, udp_throughput_file):
    print(f"Parsing TCP trace file: {tcp_trace}")
    tcp_metrics = parse_trace_file(tcp_trace, 'tcp')
    
    print(f"Parsing UDP trace file: {udp_trace}")
    udp_metrics = parse_trace_file(udp_trace, 'cbr')
    
    print(f"Parsing TCP throughput file: {tcp_throughput_file}")
    tcp_throughput_df = parse_throughput_file(tcp_throughput_file)
    
    print(f"Parsing UDP throughput file: {udp_throughput_file}")
    udp_throughput_df = parse_throughput_file(udp_throughput_file)
    
    tcp_metrics['throughput_over_time'] = tcp_throughput_df
    udp_metrics['throughput_over_time'] = udp_throughput_df
    
    tcp_throughput_avg = calculate_average(tcp_throughput_df) if not tcp_throughput_df.empty else tcp_metrics['throughput']
    udp_throughput_avg = calculate_average(udp_throughput_df) if not udp_throughput_df.empty else udp_metrics['throughput']
    
    # Calculate averages
    avg_metrics = {
        'tcp': {
            'rtt': calculate_average(tcp_metrics['rtt']),
            'delay': calculate_average(tcp_metrics['delay']),
            'jitter': calculate_average(tcp_metrics['jitter']),
            'throughput': tcp_metrics['throughput'],
            'throughput_measured': tcp_throughput_avg,
            'packet_loss': tcp_metrics['packet_loss']
        },
        'udp': {
            'rtt': calculate_average(udp_metrics['rtt']),
            'delay': calculate_average(udp_metrics['delay']),
            'jitter': calculate_average(udp_metrics['jitter']),
            'throughput': udp_metrics['throughput'],
            'throughput_measured': udp_throughput_avg,
            'packet_loss': udp_metrics['packet_loss']
        }
    }
    
    #Performance metrics
    print("\n" + "="*50)
    print("PERFORMANCE METRICS COMPARISON")
    print("="*50)
    
    print("\nTCP Metrics:")
    print(f"Average RTT: {avg_metrics['tcp']['rtt']:.4f} seconds")
    print(f"Average Jitter: {avg_metrics['tcp']['jitter']:.4f} seconds")
    print(f"Average Delay: {avg_metrics['tcp']['delay']:.4f} seconds")
    
    if not tcp_throughput_df.empty:
        print(f"Measured Throughput (from throughput.tr): {avg_metrics['tcp']['throughput_measured']:.2f} bits/sec ({avg_metrics['tcp']['throughput_measured']/1024:.2f} Kbps)")
    print(f"Calculated Throughput (from trace): {avg_metrics['tcp']['throughput']:.2f} bytes/sec ({avg_metrics['tcp']['throughput']/1024:.2f} KB/sec)")
    
    print(f"Sent Packets: {tcp_metrics['sent_packets']}")
    print(f"Total Time: {tcp_metrics['total_time']:.4f} seconds")
    
    print("\nUDP Metrics:")
    print(f"Average RTT: {avg_metrics['udp']['rtt']:.4f} seconds")
    print(f"Average Jitter: {avg_metrics['udp']['jitter']:.4f} seconds")
    print(f"Average Delay: {avg_metrics['udp']['delay']:.4f} seconds")
    
    if not udp_throughput_df.empty:
        print(f"Measured Throughput (from throughput.tr): {avg_metrics['udp']['throughput_measured']:.2f} bits/sec ({avg_metrics['udp']['throughput_measured']/1024:.2f} Kbps)")
    print(f"Calculated Throughput (from trace): {avg_metrics['udp']['throughput']:.2f} bytes/sec ({avg_metrics['udp']['throughput']/1024:.2f} KB/sec)")
    
    print(f"Sent Packets: {udp_metrics['sent_packets']}, Received Packets: {udp_metrics['received_packets']}")
    print(f"Packet Loss: {avg_metrics['udp']['packet_loss']:.2f}%")
    print(f"Total Time: {udp_metrics['total_time']:.4f} seconds")
    
    #Comparison plots
    generate_plots(tcp_metrics, udp_metrics, avg_metrics)
    
def generate_plots(tcp_metrics, udp_metrics, avg_metrics):
    plt.style.use('ggplot')
    
    os.makedirs('results', exist_ok=True)
    
    #RTT Comparison
    if not tcp_metrics['rtt'].empty or not udp_metrics['rtt'].empty:
        plt.figure(figsize=(10, 6))
        
        if not tcp_metrics['rtt'].empty:
            plt.plot(tcp_metrics['rtt']['time'], tcp_metrics['rtt']['value'], 
                     label=f"TCP RTT (avg: {avg_metrics['tcp']['rtt']:.4f}s)",
                     color='blue', alpha=0.7)
            
        if not udp_metrics['rtt'].empty:
            plt.plot(udp_metrics['rtt']['time'], udp_metrics['rtt']['value'], 
                     label=f"UDP RTT (avg: {avg_metrics['udp']['rtt']:.4f}s)",
                     color='green', alpha=0.7)
            
        plt.title("Round Trip Time (RTT) Comparison", fontsize=14)
        plt.xlabel("Simulation Time (seconds)", fontsize=12)
        plt.ylabel("RTT (seconds)", fontsize=12)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('results/rtt_comparison.png')
        print("Saved RTT comparison plot to results/rtt_comparison.png")
    
    #Jitter Comparison
    if not tcp_metrics['jitter'].empty or not udp_metrics['jitter'].empty:
        plt.figure(figsize=(10, 6))
        
        if not tcp_metrics['jitter'].empty:
            plt.plot(tcp_metrics['jitter']['time'], tcp_metrics['jitter']['value'], 
                     label=f"TCP Jitter (avg: {avg_metrics['tcp']['jitter']:.4f}s)",
                     color='orange', alpha=0.7)
            
        if not udp_metrics['jitter'].empty:
            plt.plot(udp_metrics['jitter']['time'], udp_metrics['jitter']['value'], 
                     label=f"UDP Jitter (avg: {avg_metrics['udp']['jitter']:.4f}s)",
                     color='purple', alpha=0.7)
            
        plt.title("Jitter Comparison", fontsize=14)
        plt.xlabel("Simulation Time (seconds)", fontsize=12)
        plt.ylabel("Jitter (seconds)", fontsize=12)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('results/jitter_comparison.png')
        print("Saved jitter comparison plot to results/jitter_comparison.png")
    
    #Delay Comparison
    if not tcp_metrics['delay'].empty or not udp_metrics['delay'].empty:
        plt.figure(figsize=(10, 6))
        
        if not tcp_metrics['delay'].empty:
            plt.plot(tcp_metrics['delay']['time'], tcp_metrics['delay']['value'], 
                     label=f"TCP Delay (avg: {avg_metrics['tcp']['delay']:.4f}s)",
                     color='red', alpha=0.7)
            
        if not udp_metrics['delay'].empty:
            plt.plot(udp_metrics['delay']['time'], udp_metrics['delay']['value'], 
                     label=f"UDP Delay (avg: {avg_metrics['udp']['delay']:.4f}s)",
                     color='cyan', alpha=0.7)
            
        plt.title("End-to-End Delay Comparison", fontsize=14)
        plt.xlabel("Simulation Time (seconds)", fontsize=12)
        plt.ylabel("Delay (seconds)", fontsize=12)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('results/delay_comparison.png')
        print("Saved delay comparison plot to results/delay_comparison.png")
    
    #Throughput Over Time
    plt.figure(figsize=(10, 6))
    
    if not tcp_metrics['throughput_over_time'].empty:
        plt.plot(tcp_metrics['throughput_over_time']['time'], 
                 tcp_metrics['throughput_over_time']['value'] / 1024, 
                 label=f"TCP Throughput (avg: {avg_metrics['tcp']['throughput_measured']/1024:.2f} Kbps)",
                 color='blue', alpha=0.7)
    
    if not udp_metrics['throughput_over_time'].empty:
        plt.plot(udp_metrics['throughput_over_time']['time'], 
                 udp_metrics['throughput_over_time']['value'] / 1024, 
                 label=f"UDP Throughput (avg: {avg_metrics['udp']['throughput_measured']/1024:.2f} Kbps)",
                 color='green', alpha=0.7)
    
    plt.title("Throughput Over Time", fontsize=14)
    plt.xlabel("Simulation Time (seconds)", fontsize=12)
    plt.ylabel("Throughput (Kbps)", fontsize=12)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('results/throughput_over_time.png')
    print("Saved throughput over time plot to results/throughput_over_time.png")
    
    #Average Throughput Comparison
    plt.figure(figsize=(8, 6))
    protocols = ['TCP', 'UDP']
    
    # Use measured throughput if available, otherwise use calculated throughput
    tcp_throughput = avg_metrics['tcp']['throughput_measured'] if 'throughput_measured' in avg_metrics['tcp'] and avg_metrics['tcp']['throughput_measured'] > 0 else avg_metrics['tcp']['throughput'] * 8
    udp_throughput = avg_metrics['udp']['throughput_measured'] if 'throughput_measured' in avg_metrics['udp'] and avg_metrics['udp']['throughput_measured'] > 0 else avg_metrics['udp']['throughput'] * 8
    
    throughputs = [tcp_throughput, udp_throughput]
    throughputs_kb = [t/1024 for t in throughputs]
    
    bars = plt.bar(protocols, throughputs_kb, color=['blue', 'green'], alpha=0.7)
    plt.title("Average Throughput Comparison", fontsize=14)
    plt.ylabel("Throughput (Kbps)", fontsize=12)
    plt.grid(True, axis='y')
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig('results/avg_throughput_comparison.png')
    print("Saved average throughput comparison plot to results/avg_throughput_comparison.png")

    #Radar Chart
    plt.figure(figsize=(10, 8))
    
    metrics = ['Throughput', 'RTT (inv)', 'Delay (inv)', 'Jitter (inv)']

    max_throughput = max(tcp_throughput, udp_throughput) if max(tcp_throughput, udp_throughput) > 0 else 1
    max_rtt = max(avg_metrics['tcp']['rtt'], avg_metrics['udp']['rtt']) if max(avg_metrics['tcp']['rtt'], avg_metrics['udp']['rtt']) > 0 else 1
    max_delay = max(avg_metrics['tcp']['delay'], avg_metrics['udp']['delay']) if max(avg_metrics['tcp']['delay'], avg_metrics['udp']['delay']) > 0 else 1
    max_jitter = max(avg_metrics['tcp']['jitter'], avg_metrics['udp']['jitter']) if max(avg_metrics['tcp']['jitter'], avg_metrics['udp']['jitter']) > 0 else 1

    tcp_values = [
    tcp_throughput / max_throughput if max_throughput > 0 else 0,
    1 - (avg_metrics['tcp']['rtt'] / max_rtt) if avg_metrics['tcp']['rtt'] > 0 and max_rtt > 0 else 1,
    1 - (avg_metrics['tcp']['delay'] / max_delay) if avg_metrics['tcp']['delay'] > 0 and max_delay > 0 else 1,
    1 - (avg_metrics['tcp']['jitter'] / max_jitter) if avg_metrics['tcp']['jitter'] > 0 and max_jitter > 0 else 1
    ]

    udp_values = [
        udp_throughput / max_throughput if max_throughput > 0 else 0,
        1 - (avg_metrics['udp']['rtt'] / max_rtt) if avg_metrics['udp']['rtt'] > 0 and max_rtt > 0 else 1,
        1 - (avg_metrics['udp']['delay'] / max_delay) if avg_metrics['udp']['delay'] > 0 and max_delay > 0 else 1,
        1 - (avg_metrics['udp']['jitter'] / max_jitter) if avg_metrics['udp']['jitter'] > 0 and max_jitter > 0 else 1
    ]

    tcp_values.append(tcp_values[0])
    udp_values.append(udp_values[0])
    metrics.append(metrics[0])

    angles = np.linspace(0, 2*np.pi, len(metrics)-1, endpoint=False).tolist()
    angles.append(angles[0])  

    ax = plt.subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2)  
    ax.set_theta_direction(-1)  

    ax.plot(angles, tcp_values, 'b-', linewidth=2, label='TCP')
    ax.fill(angles, tcp_values, 'b', alpha=0.25)

    ax.plot(angles, udp_values, 'g-', linewidth=2, label='UDP')
    ax.fill(angles, udp_values, 'g', alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics[:-1], fontsize=10)

    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8'], fontsize=8)
    ax.grid(True)

    plt.title('Protocol Performance Comparison\n(Higher values indicate better performance)', fontsize=14)
    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))

    plt.tight_layout()
    plt.savefig('results/performance_radar.png')
    print("Saved performance radar chart to results/performance_radar.png")
    
    plt.show()

def main():
    """Main function to run the analysis"""
    tcp_trace = 'tcp_output.tr'
    udp_trace = 'udp_output.tr'
    tcp_throughput = 'tcp_throughput.tr'
    udp_throughput = 'udp_throughput.tr'
    
    if not os.path.exists(tcp_trace):
        print(f"Error: TCP trace file {tcp_trace} not found.")
        return
        
    if not os.path.exists(udp_trace):
        print(f"Error: UDP trace file {udp_trace} not found.")
        return
    
    print("\nNetwork Performance Analysis Tool")
    print("--------------------------------")
    analyze_trace_files(tcp_trace, udp_trace, tcp_throughput, udp_throughput)
    print("\nAnalysis complete! Results saved in the 'results' directory.")

if __name__ == "__main__":
    main()